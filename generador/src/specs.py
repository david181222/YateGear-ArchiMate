"""Revisa el YAML de especificaciones de un contexto contra modelo-ddd.json.

No genera nada. Junta todos los errores y termina con código 1 si el YAML:
  - deja sin especificar un elemento del contexto o nombra uno que no existe;
  - tiene una clave desconocida o repetida, un tipo no permitido o un estado
    fuera de la lista cerrada;
  - declara para un comando eventos distintos de los que ese comando dispara
    en el modelo (ni más ni menos);
  - usa un dato que no está disponible por su nombre, con el mismo tipo, donde
    se necesita (regla de los datos, ver el comentario al inicio del YAML).

uso: python src/specs.py <modelo-ddd.json> <specs.yaml>
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import yaml

import tipos

ESCRIBEN = ("escritura", "lectura y escritura")


# ------------------------------------------------------------ YAML sin claves repetidas

class _Cargador(yaml.SafeLoader):
    pass


def _mapa_sin_repetidos(loader, node, deep=False):
    vistas = set()
    for k_node, _ in node.value:
        k = loader.construct_object(k_node, deep=deep)
        if k in vistas:
            raise yaml.constructor.ConstructorError(None, None, f'clave repetida "{k}"', k_node.start_mark)
        vistas.add(k)
    return loader.construct_mapping(node, deep)


_Cargador.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapa_sin_repetidos)


def cargar_yaml(ruta: str):
    with open(ruta, encoding="utf-8") as f:
        return yaml.load(f, Loader=_Cargador)


# ------------------------------------------------------------ tipos y valores

def mismo_tipo(a: dict, b: dict) -> bool:
    """Igual base, lista y enum. El sufijo ? no cuenta: un dato opcional puede ir donde va uno obligatorio."""
    return a["base"] == b["base"] and a["lista"] == b["lista"] and a["enum"] == b["enum"]


def valor_valido(v, t: dict) -> bool:
    if v is None:
        return t["opcional"]
    if t["lista"]:
        uno = {**t, "lista": False, "opcional": False}
        return isinstance(v, list) and all(valor_valido(x, uno) for x in v)
    b = t["base"]
    if b == "enum":
        return isinstance(v, str) and v in t["enum"]["valores"]
    if b == "string":
        return isinstance(v, str)
    if b == "int":
        return isinstance(v, int) and not isinstance(v, bool)
    if b == "decimal":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if b == "bool":
        return isinstance(v, bool)
    try:                                  # las fechas van como texto entre comillas
        if b == "DateOnly":
            return isinstance(v, str) and len(v) == 10 and bool(datetime.date.fromisoformat(v))
        if b == "DateTime":
            return isinstance(v, str) and "T" in v and bool(datetime.datetime.fromisoformat(v))
    except ValueError:
        return False
    return False


class Revisor:
    def __init__(self, modelo: dict, spec, nombre_archivo: str):
        self.m = modelo
        self.s = spec
        self.archivo = nombre_archivo
        self.errores: list[str] = []
        self.avisos: list[str] = []
        self.enums: dict[str, list[str]] = {}
        self.varios_origenes: list[str] = []   # datos que llegan de más de un origen (informativo)

    # ------------------------------------------------------------ utilidades
    def error(self, donde: str, texto: str):
        self.errores.append(f"[{donde}] {texto}")

    def aviso(self, donde: str, texto: str):
        self.avisos.append(f"[{donde}] {texto}")

    def mapa(self, x, donde: str, permitidas=None, obligatorias=()) -> dict:
        if x is None:
            x = {}
        if not isinstance(x, dict):
            self.error(donde, f"se esperaba una sección con claves y se encontró {type(x).__name__}")
            return {}
        if permitidas is not None:
            for k in x:
                if k not in permitidas:
                    self.error(donde, f'clave desconocida "{k}"; se permiten: {", ".join(permitidas)}')
        for k in obligatorias:
            if k not in x:
                self.error(donde, f'falta la clave "{k}"')
        return x

    def lista(self, x, donde: str) -> list:
        if x is None:
            return []
        if not isinstance(x, list):
            self.error(donde, f"se esperaba una lista y se encontró {type(x).__name__}")
            return []
        return x

    def tipo(self, texto, donde: str) -> dict | None:
        try:
            t = tipos.interpretar(texto)
        except tipos.TipoInvalido as e:
            self.error(donde, str(e))
            return None
        if t["enum"]:
            n, v = t["enum"]["nombre"], t["enum"]["valores"]
            if self.enums.setdefault(n, v) != v:
                self.error(donde, f'el enum "{n}" ya existe con otros valores: {", ".join(self.enums[n])}')
        return t

    def campos(self, x, donde: str, libres: bool = False, permitidos=()) -> dict[str, dict]:
        """Datos "nombre: tipo". La identidad y el estado se agregan solos, así que solo se
        pueden escribir donde se piden o se devuelven (libres=True): entrada de un SA y salida de una consulta."""
        out = {}
        for nombre, texto in self.mapa(x, donde).items():
            if not isinstance(nombre, str) or not nombre.strip():
                self.error(donde, f"nombre de dato vacío o inválido: {nombre!r}")
                continue
            if not libres and nombre in (self.id_nombre, "estado") and nombre not in permitidos:
                self.error(donde, f'"{nombre}" se agrega solo; no se escribe en el YAML')
                continue
            t = self.tipo(texto, f'{donde} > {nombre}')
            if t:
                out[nombre] = t
        return out

    def cubre(self, seccion: str, del_yaml: dict, del_modelo: dict, tipo: str):
        for n in sorted(set(del_modelo) - set(del_yaml)):
            self.error(seccion, f'falta en el YAML: {tipo} "{n}" ({del_modelo[n]["id"]})')
        for n in sorted(set(del_yaml) - set(del_modelo)):
            self.error(seccion, f'"{n}" no existe en el modelo como {tipo} del contexto')

    def agregar(self, bolsa: dict, nuevos: dict, donde: str):
        for n, t in nuevos.items():
            if n in bolsa and not mismo_tipo(bolsa[n], t):
                self.error(donde, f'el dato "{n}" ya existe como {bolsa[n]["tipo"]} y aquí llega como {t["tipo"]}')
            else:
                bolsa[n] = t

    def pide(self, bolsa: dict, necesarios: dict, donde: str, quien: str, propios=frozenset()):
        """Revisa que cada dato necesario esté en la bolsa, con su tipo y con un solo origen.

        propios: nombres que llegan por la entrada o por un SA; esos no dependen de la raíz.
        """
        for n, t in necesarios.items():
            if n in self.ambiguos and n not in propios:
                self.error(donde, f'{quien} usa "{n}", que puede venir de {" y de ".join(self.ambiguos[n])}')
            elif n not in bolsa:
                self.error(donde, f'{quien} necesita "{n}" ({t["tipo"]}) y no está disponible por ese nombre')
            elif not mismo_tipo(bolsa[n], t):
                self.error(donde, f'{quien} necesita "{n}" como {t["tipo"]} y está disponible como {bolsa[n]["tipo"]}')

    def estados_validos(self, valores, donde: str) -> list[str]:
        out = []
        for e in self.lista(valores, donde) if isinstance(valores, list) else [valores]:
            if e not in self.estados:
                self.error(donde, f'"{e}" no es un estado de la raíz; estados: {", ".join(self.estados)}')
            else:
                out.append(e)
        return out

    def condicion(self, si, bolsa: dict, donde: str, propios=frozenset()) -> dict[str, set]:
        out = {}
        for campo, valores in self.mapa(si, donde).items():
            if campo in self.ambiguos and campo not in propios:
                self.error(donde, f'la condición usa "{campo}", que puede venir de {" y de ".join(self.ambiguos[campo])}')
                continue
            if campo not in bolsa:
                self.error(donde, f'la condición usa "{campo}", que no está disponible')
                continue
            t = bolsa[campo]
            if t["lista"]:
                self.error(donde, f'la condición no puede usar la lista "{campo}"')
                continue
            vals = self.lista(valores, f"{donde} > {campo}")
            for v in vals:
                if not valor_valido(v, {**t, "opcional": False}):
                    self.error(donde, f'el valor {v!r} no es válido para "{campo}" ({t["tipo"]})')
            out[campo] = set(map(str, vals))
        return out

    def revisar_valores(self, valores, bolsa: dict, donde: str, todos: dict) -> list[str]:
        """Valores fijos: solo para datos de la raíz o de sus objetos de valor, cuyo tipo sale del modelo.
        Los agrega a la bolsa y devuelve sus nombres."""
        out = []
        for k, v in self.mapa(valores, donde).items():
            t_v = (todos.get(k) or self.componentes.get(k)) if k not in (self.id_nombre, "estado") else None
            if t_v is None:
                self.error(donde, f'"{k}" no es un campo de la raíz ni de sus objetos de valor')
            elif not valor_valido(v, t_v):
                self.error(donde, f'el valor {v!r} no es válido para "{k}" ({t_v["tipo"]})')
            else:
                self.agregar(bolsa, {k: t_v}, donde)
                out.append(k)
        return out

    OPERACIONES_LISTA = ("agregar", "reemplazar", "quitar")

    def revisar_guarda(self, guarda: list, bolsa: dict, propios: set, d: str, campos_raiz: dict, vos: dict,
                       nombre_raiz: str) -> dict:
        """Lo que se guarda en la raíz: objetos de valor y campos por su nombre, {campo: dato} para guardar un dato
        con otro nombre, y en un objeto de valor con Cardinalidad Muchos (G4) {lista: agregar}, {lista: {reemplazar:
        [claves]}} o {lista: {quitar: [claves]}}. Cada dato debe tener un solo destino. Devuelve lo guardado."""
        guardados, destinos = {}, {}

        def pedir_vo(v, solo=None):
            for campo in v["campos"]:
                if solo is not None and campo["nombre"] not in solo:
                    continue
                if campo["nombre"] in bolsa or not campo["opcional"] or solo is not None:
                    self.pide(bolsa, {campo["nombre"]: campo}, d, f'el objeto de valor "{v["nombre"]}"', propios)

        for g in guarda:
            if isinstance(g, dict) and len(g) == 1 and next(iter(g)) in vos:     # operación sobre una lista
                nombre_vo, op = next(iter(g.items()))
                v = vos[nombre_vo]
                if v["cardinalidad"] != "Muchos":
                    self.error(d, f'"{nombre_vo}" tiene Cardinalidad {v["cardinalidad"]}: se guarda por su nombre, sin operación')
                    continue
                if op == "agregar":
                    claves = None
                elif isinstance(op, dict) and len(op) == 1 and next(iter(op)) in ("reemplazar", "quitar"):
                    op, claves = next(iter(op.items()))
                    claves = self.lista(claves, f"{d} > {nombre_vo} > {op}")
                    nombres_vo = {c["nombre"] for c in v["campos"]}
                    for k in claves:
                        if k not in nombres_vo:
                            self.error(d, f'la clave "{k}" no es un campo de "{nombre_vo}"')
                    if not claves:
                        self.error(d, f'{op} necesita la clave: los campos con que se encuentra el elemento de "{nombre_vo}"')
                else:
                    self.error(d, f'en "{nombre_vo}" (una lista) se escribe agregar, {{reemplazar: [claves]}} o {{quitar: [claves]}}')
                    continue
                pedir_vo(v, solo=set(claves) if op == "quitar" else None)
                if op != "quitar":
                    for campo in v["campos"]:
                        guardados[campo["nombre"]] = campo
                destinos.setdefault(nombre_vo, []).append(op)
            elif isinstance(g, dict):                     # {campo de la raíz: dato}: guarda un dato con otro nombre
                if len(g) != 1:
                    self.error(d, "una correspondencia es {campo de la raíz: dato}, una por línea")
                    continue
                campo, dato = next(iter(g.items()))
                if campo not in campos_raiz:
                    self.error(d, f'"{campo}" no es un campo de la raíz {nombre_raiz} ni un objeto de valor')
                    continue
                if not isinstance(dato, str) or dato not in bolsa:
                    self.error(d, f'"{campo}" se guarda con "{dato}", que el comando no tiene')
                elif not mismo_tipo(bolsa[dato], campos_raiz[campo]):
                    self.error(d, f'"{dato}" es {bolsa[dato]["tipo"]} y "{campo}" es {campos_raiz[campo]["tipo"]}')
                guardados[campo] = campos_raiz[campo]
                destinos.setdefault(campo, []).append(f'la raíz "{nombre_raiz}"')
            elif not isinstance(g, str):
                self.error(d, f"{g!r} no es un nombre, una correspondencia ni una operación sobre una lista")
            elif g in vos:
                v = vos[g]
                if v["cardinalidad"] == "Muchos":
                    self.error(d, f'"{g}" tiene Cardinalidad Muchos: se escribe {{{g}: agregar}}, {{{g}: {{reemplazar: [claves]}}}} '
                                  f'o {{{g}: {{quitar: [claves]}}}}')
                    continue
                pedir_vo(v)
                for campo in v["campos"]:
                    guardados[campo["nombre"]] = campo
                    destinos.setdefault(campo["nombre"], []).append(f'"{g}"')
            elif g in campos_raiz:
                self.pide(bolsa, {g: campos_raiz[g]}, d, f'el campo "{g}" de la raíz', propios)
                guardados[g] = campos_raiz[g]
                destinos.setdefault(g, []).append(f'la raíz "{nombre_raiz}"')
            else:
                self.error(d, f'"{g}" no es un objeto de valor ni un campo de la raíz {nombre_raiz}')
        for nombre_dato, lugares in sorted(destinos.items()):
            if len(lugares) > 1:
                self.error(d, f'"{nombre_dato}" puede ir a más de un destino: {" y ".join(lugares)}')
        return guardados

    # ------------------------------------------------------------ raíces (una por agregado, G2)
    def preparar_raiz(self, nombre_raiz: str, ag: dict, r_yaml) -> dict:
        """Identidad, estado y datos de una raíz. No cambia la raíz actual (ver usar)."""
        r = self.mapa(r_yaml, f"raices > {nombre_raiz}", ["identidad", "estado"], ["identidad", "estado"])
        di = f"raices > {nombre_raiz} > identidad"
        ident = self.mapa(r.get("identidad"), di, ["nombre", "tipo", "prefijo", "digitos", "de"], ["nombre", "tipo"])
        id_nombre = ident.get("nombre", "")
        id_tipo = self.tipo(ident.get("tipo"), f"{di} > tipo")
        if id_tipo and (id_tipo["base"] != "string" or id_tipo["lista"] or id_tipo["opcional"]):
            self.error(di, "la identidad debe ser string obligatorio")
        campos_raiz = {c["nombre"]: c for c in ag["raiz"]["campos"]}
        # La identidad es un consecutivo (prefijo y digitos) o se forma con datos (de), una de las dos (G3).
        # Con un solo dato que se llama como la identidad, la identidad es recibida: llega con ese nombre.
        id_de, componentes, recibida = None, {}, False
        consecutivo = "prefijo" in ident or "digitos" in ident
        if consecutivo == ("de" in ident):
            self.error(di, "la identidad es un consecutivo (prefijo y digitos) o se forma con datos (de); una de las dos")
        elif consecutivo:
            if not isinstance(ident.get("prefijo"), str):
                self.error(di, "prefijo debe ser texto, por ejemplo ARR-")
            if not isinstance(ident.get("digitos"), int) or isinstance(ident.get("digitos"), bool) or ident.get("digitos", 0) < 1:
                self.error(di, "digitos debe ser un entero mayor que 0")
        else:
            de = self.mapa(ident.get("de"), f"{di} > de")
            if not de:
                self.error(f"{di} > de", "di con qué datos se forma la identidad, en orden")
            id_de = []
            recibida = list(de) == [id_nombre]
            for parte, texto in de.items():
                dp = f"{di} > de > {parte}"
                if parte == id_nombre and recibida:     # identidad recibida: su tipo es el de la identidad
                    id_de.append(parte)
                    continue
                if parte in (id_nombre, "estado"):
                    self.error(dp, "la identidad no se forma con la identidad (salvo si es su único dato) ni con el estado")
                    continue
                if texto is None:                         # campo de la raíz: su tipo sale del modelo
                    if parte not in campos_raiz:
                        self.error(dp, f'no es un campo de la raíz {nombre_raiz}; si no lo es, escribe su tipo')
                        continue
                    t_parte = tipos.interpretar(campos_raiz[parte]["tipo"])
                else:                                     # dato que no es campo: la raíz lo guarda como parte de su identidad
                    if parte in campos_raiz:
                        self.error(dp, "es un campo de la raíz: no lleva tipo (sale del modelo)")
                        continue
                    t_parte = self.tipo(texto, dp)
                    if not t_parte:
                        continue
                    componentes[parte] = t_parte
                if t_parte["lista"] or t_parte["opcional"] or t_parte["base"] not in ("string", "int", "enum"):
                    self.error(dp, f'una parte de la identidad es string, int o enum, obligatoria; aquí es {t_parte["tipo"]}')
                id_de.append(parte)
        estado_t = self.tipo(r.get("estado"), f"raices > {nombre_raiz} > estado")
        if estado_t and (estado_t["base"] != "enum" or estado_t["opcional"]):
            self.error(f"raices > {nombre_raiz} > estado", "el estado debe ser un enum obligatorio")
            estado_t = None

        # Campos de la raíz y de sus objetos de valor. Un nombre que está en dos de ellos es ambiguo:
        # solo es error si un comando, evento o consulta lo usa sin que llegue por su entrada o por un SA.
        vos = {v["nombre"]: v for v in ag["objetos_valor"] + ag["entidades"]}
        todos, origenes = {}, {}
        for dueno, lista in [(nombre_raiz, ag["raiz"]["campos"])] + [(v["nombre"], v["campos"]) for v in vos.values()]:
            for c in lista:
                if c["nombre"] in (id_nombre, "estado"):
                    self.error("modelo", f'el campo "{c["nombre"]}" de "{dueno}" se llama igual que la identidad o el estado')
                origenes.setdefault(c["nombre"], []).append(f'"{dueno}"')
                todos.setdefault(c["nombre"], c)
        for parte in componentes:
            if parte in todos:
                self.error(f"raices > {nombre_raiz} > identidad > de > {parte}", f"se llama igual que un campo de {origenes[parte][0]}")
        base = {**({id_nombre: id_tipo} if id_tipo else {}), **componentes}
        # Los campos de una lista (objeto de valor con Cardinalidad Muchos) no son datos sueltos de la raíz: no
        # están disponibles por su nombre, aunque sí se pueden fijar con valores al guardar en la lista.
        en_listas = {c["nombre"] for v in vos.values() if v["cardinalidad"] == "Muchos" for c in v["campos"]}
        sueltos = {k: c for k, c in todos.items() if k not in en_listas or k in campos_raiz}
        return {"nombre": nombre_raiz, "id": ag["raiz"]["id"], "agregado_id": ag["id"],
                "id_nombre": id_nombre, "id_tipo": id_tipo, "id_de": id_de, "componentes": componentes,
                "consecutivo": consecutivo, "recibida": recibida,
                "estado_t": estado_t, "estados": estado_t["enum"]["valores"] if estado_t else [],
                "campos_raiz": campos_raiz, "vos": vos, "todos": todos,
                "ambiguos": {n: l for n, l in origenes.items() if len(l) > 1},
                "base": base, "con_raiz": {**base, **sueltos, **({"estado": estado_t} if estado_t else {})}}

    def usar(self, rc: dict):
        """Hace de rc la raíz actual (la usan pide, campos, condicion y estados_validos) y devuelve sus datos."""
        self.rc = rc
        self.id_nombre, self.id_tipo, self.estados = rc["id_nombre"], rc["id_tipo"], rc["estados"]
        self.ambiguos, self.componentes, self.id_de = rc["ambiguos"], rc["componentes"], rc["id_de"]
        return rc["con_raiz"], rc["todos"], rc["campos_raiz"], rc["vos"], rc["base"], rc["estado_t"], rc["nombre"]

    # ------------------------------------------------------------ revisión
    def revisar(self):
        s = self.mapa(self.s, "archivo", ["contexto", "raices", "comandos", "eventos", "consultas",
                                          "eventos_de_otros_contextos", "servicios_sa", "escenarios"],
                      ["contexto", "raices", "comandos", "eventos", "consultas", "servicios_sa"])
        ctxs = {c["nombre"]: c for c in self.m["contextos"]}
        if s.get("contexto") not in ctxs:
            self.error("contexto", f'"{s.get("contexto")}" no está en el JSON; contextos: {", ".join(ctxs)}')
            return
        ctx = ctxs[s["contexto"]]
        for e in ctx["enums"]:
            self.enums[e["nombre"]] = e["valores"]

        # ---- raíces
        agregados = {a["raiz"]["id"]: a for a in ctx["agregados"]}
        raices_m = {a["raiz"]["nombre"]: {"id": a["raiz"]["id"]} for a in ctx["agregados"]}
        raices_y = self.mapa(s.get("raices"), "raices")
        self.cubre("raices", raices_y, raices_m, "raíz")
        if not raices_m:
            self.error("raices", "el contexto no tiene agregados")
            return
        # Cada raíz se prepara por separado; cada comando, evento, consulta y paso usa la de su agregado (G2).
        self.raices = {n: self.preparar_raiz(n, agregados[raices_m[n]["id"]], raices_y.get(n)) for n in sorted(raices_m)}
        self.raiz_por_id = {rc["id"]: rc for rc in self.raices.values()}
        self.raiz_por_agregado = {rc["agregado_id"]: rc for rc in self.raices.values()}
        con_raiz, todos, campos_raiz, vos, base, estado_t, nombre_raiz = self.usar(next(iter(self.raices.values())))

        # ---- servicios SA (antes que los comandos, porque los comandos los usan)
        sas_m = {x["nombre"]: x for x in ctx["servicios_sa"]}
        sas_y = self.mapa(s.get("servicios_sa"), "servicios_sa")
        self.cubre("servicios_sa", sas_y, sas_m, "servicio SA")
        sas = {}
        for n in sorted(set(sas_y) & set(sas_m)):
            d = f"servicios_sa > {n}"
            x = self.mapa(sas_y[n], d, ["entrada", "salida", "respuesta_por_defecto", "casos"],
                          ["entrada", "salida", "respuesta_por_defecto"])
            ent = self.campos(x.get("entrada"), f"{d} > entrada", libres=True)
            sal = self.campos(x.get("salida"), f"{d} > salida")

            def respuesta(resp, donde):
                resp = self.mapa(resp, donde)
                for k in sorted(set(sal) - set(resp)):
                    self.error(donde, f'falta el valor de "{k}"')
                for k, v in resp.items():
                    if k not in sal:
                        self.error(donde, f'"{k}" no está en la salida del servicio')
                    elif not valor_valido(v, sal[k]):
                        self.error(donde, f'el valor {v!r} no es válido para "{k}" ({sal[k]["tipo"]})')

            respuesta(x.get("respuesta_por_defecto"), f"{d} > respuesta_por_defecto")
            for i, caso in enumerate(self.lista(x.get("casos"), f"{d} > casos"), 1):
                caso = self.mapa(caso, f"{d} > casos {i}", ["si", "respuesta"], ["si", "respuesta"])
                self.condicion(caso.get("si"), ent, f"{d} > casos {i} > si")
                respuesta(caso.get("respuesta"), f"{d} > casos {i} > respuesta")
            sas[n] = {"entrada": ent, "salida": sal, "usado_por": []}

        # ---- comandos
        cmds_m = {c["nombre"]: c for c in ctx["comandos"]}
        evs_m = {e["nombre"]: e for e in ctx["eventos"]}
        ev_por_id = {e["id"]: e["nombre"] for e in ctx["eventos"]}
        cmds_y = self.mapa(s.get("comandos"), "comandos")
        self.cubre("comandos", cmds_y, cmds_m, "comando")
        bolsas_evento: dict[str, list[tuple[str, dict]]] = {}
        entradas_cmd, crean = {}, []
        # Eventos de otros contextos: los comandos que los requieren (requiere) los necesitan desde ya.
        ext_y = s.get("eventos_de_otros_contextos") if isinstance(s.get("eventos_de_otros_contextos"), dict) else {}
        self.requeridos: dict[str, list[str]] = {}          # evento de otro contexto -> comandos que lo requieren
        crean_por_raiz: dict[str, list[str]] = {}
        for n in sorted(set(cmds_y) & set(cmds_m)):
            d = f"comandos > {n}"
            m = cmds_m[n]
            rc = self.raiz_por_id.get(m["raiz_id"])
            if rc is None:
                continue
            con_raiz, todos, campos_raiz, vos, base, estado_t, nombre_raiz = self.usar(rc)
            c = self.mapa(cmds_y[n], d, ["crea", "desde", "a", "entrada", "valores", "requiere", "usa", "guarda", "eventos",
                                         "resultados"], ["entrada"])
            crea = c.get("crea", False)
            if crea not in (True, False, "si_no_existe"):
                self.error(d, "crea es true, false o si_no_existe")
                crea = False
            si_no_existe = crea == "si_no_existe"         # carga la raíz y, si no existe, la crea vacía
            if si_no_existe:
                crea = False
                if not rc["recibida"]:
                    self.error(d, "crea: si_no_existe necesita una identidad recibida (de con un solo dato, la identidad): "
                                  "la raíz nueva toma la identidad que trae el comando")
                for campo in campos_raiz.values():
                    if not campo["opcional"]:
                        self.error(d, f'crea: si_no_existe crea la raíz vacía, y su campo "{campo["nombre"]}" es obligatorio')
                for v in vos.values():
                    if v["cardinalidad"] == "Uno":
                        self.error(d, f'crea: si_no_existe crea la raíz vacía, y "{v["nombre"]}" tiene Cardinalidad Uno')
            if crea or si_no_existe:
                crean.append(n)
                crean_por_raiz.setdefault(nombre_raiz, []).append(n)
                if m["acceso"] not in ESCRIBEN:
                    self.error(d, f"el comando crea la raíz pero en el modelo su acceso es de {m['acceso']}")
            # El comando que crea una raíz con identidad recibida la trae en su entrada.
            ent = self.campos(c.get("entrada"), f"{d} > entrada", permitidos=(self.id_nombre,) if crea and rc["recibida"] else ())
            if crea and rc["recibida"] and self.id_nombre not in ent:
                self.error(f"{d} > entrada", f'crea "{nombre_raiz}", cuya identidad es recibida: falta "{self.id_nombre}" en la entrada')
            entradas_cmd[n] = {"entrada": ent, "crea": crea, "raiz": nombre_raiz}
            # El comando que crea la raíz no tiene raíz ni identidad hasta que la guarda (la identidad se
            # asigna al guardar, después de ValidarReglas): sus SA y condiciones solo usan entrada y SA.
            bolsa = {} if crea else dict(con_raiz)
            self.agregar(bolsa, ent, f"{d} > entrada")
            propios = set(ent)
            origenes_cmd = {} if crea else {k: ["raíz"] for k in todos if k in con_raiz}
            for k in ent:
                origenes_cmd.setdefault(k, []).append("entrada")

            # Valores fijos del comando: solo para datos de la raíz, cuyo tipo sale del modelo o de la identidad.
            for k in self.revisar_valores(c.get("valores"), bolsa, f"{d} > valores", todos):
                propios.add(k)
                origenes_cmd.setdefault(k, []).append("valores")

            # Eventos de otros contextos que el comando requiere (D5): si no han llegado para su identidad, 409.
            # Sus datos entran a la bolsa del comando.
            for ev in self.lista(c.get("requiere"), f"{d} > requiere"):
                x = ext_y.get(ev)
                if not isinstance(x, dict):
                    self.error(f"{d} > requiere", f'"{ev}" no está en eventos_de_otros_contextos')
                    continue
                self.requeridos.setdefault(ev, []).append(n)
                id_ev = x.get("identidad", self.id_nombre)
                if id_ev not in bolsa:
                    self.error(f"{d} > requiere", f'para buscar "{ev}" hace falta "{id_ev}" (su identidad), y el comando no lo tiene')
                elif bolsa[id_ev]["base"] != "string" or bolsa[id_ev]["lista"]:
                    self.error(f"{d} > requiere", f'"{id_ev}", la identidad de "{ev}", debe ser string')
                datos_ev = {}
                for k, tx in (x.get("datos") or {}).items():
                    try:
                        datos_ev[k] = tipos.interpretar(tx)
                    except tipos.TipoInvalido:
                        pass                              # el error se informa al revisar eventos_de_otros_contextos
                self.agregar(bolsa, datos_ev, f"{d} > requiere > {ev}")
                propios |= set(datos_ev)
                for k in datos_ev:
                    origenes_cmd.setdefault(k, []).append(f'evento "{ev}"')

            # Servicios SA que usa, en orden: piden datos de la bolsa y le agregan su salida.
            for sa in self.lista(c.get("usa"), f"{d} > usa"):
                if sa not in sas:
                    self.error(f"{d} > usa", f'"{sa}" no es un servicio SA del contexto')
                    continue
                sas[sa]["usado_por"].append(n)
                self.pide(bolsa, sas[sa]["entrada"], f"{d} > usa", f'el servicio SA "{sa}"', propios)
                self.agregar(bolsa, sas[sa]["salida"], f"{d} > usa > {sa}")
                propios |= set(sas[sa]["salida"])
                for k in sas[sa]["salida"]:
                    origenes_cmd.setdefault(k, []).append(f'SA "{sa}"')
            for k, lista_o in sorted(origenes_cmd.items()):
                if len(lista_o) > 1 and k != self.id_nombre:
                    self.varios_origenes.append(f'{n}: "{k}" llega de {", ".join(lista_o)}; se usa {lista_o[-1]}')

            # Lo que guarda en la raíz. Cada dato debe tener un solo destino (regla de los datos).
            guarda = self.lista(c.get("guarda"), f"{d} > guarda")
            if guarda and m["acceso"] not in ESCRIBEN:
                self.error(f"{d} > guarda", f"el comando guarda datos pero en el modelo su acceso a la raíz es de {m['acceso']}")
            guardados = self.revisar_guarda(guarda, bolsa, propios, f"{d} > guarda", campos_raiz, vos, nombre_raiz)
            if crea:
                for v in vos.values():
                    if v["cardinalidad"] == "Uno" and v["nombre"] not in guarda:
                        self.error(f"{d} > guarda", f'crea la raíz y no guarda "{v["nombre"]}", que tiene Cardinalidad Uno')
                for campo in campos_raiz.values():
                    if not campo["opcional"] and campo["nombre"] not in guardados:
                        self.error(f"{d} > guarda", f'crea la raíz y no guarda su campo obligatorio "{campo["nombre"]}"')
                # Identidad formada con datos: cada parte que no es campo debe estar en la bolsa (los campos ya se guardan).
                for parte in self.id_de or []:
                    if parte in self.componentes:
                        self.pide(bolsa, {parte: self.componentes[parte]}, d, "la identidad de la raíz", propios)

            # Transiciones.
            if crea and ("desde" in c or "resultados" in c):
                self.error(d, "el comando que crea la raíz no lleva desde ni resultados")
            if crea and "a" not in c:
                self.error(d, "el comando que crea la raíz debe decir su estado inicial (a)")
            desde = self.estados_validos(c["desde"], f"{d} > desde") if "desde" in c else None
            if "a" in c:
                self.estados_validos(c["a"], f"{d} > a")
            lectura = m["acceso"] not in ESCRIBEN

            # Eventos: exactamente los que el comando dispara en el modelo.
            bolsas_resultado = {}                         # evento -> (bolsa, guardados, propios) de su resultado
            del_modelo = {ev_por_id[i] for i in m["eventos"]}
            if ("eventos" in c) == ("resultados" in c):
                self.error(d, "debe tener eventos o resultados (uno de los dos)")
                del_yaml = set()
            elif "eventos" in c:
                del_yaml = set(self.lista(c["eventos"], f"{d} > eventos"))
                if "a" in c and lectura:
                    self.error(d, "el comando solo lee la raíz: no puede cambiar el estado (a)")
                if not crea and desde is None:
                    self.error(d, "falta desde: los estados desde los que se permite el comando")
            else:
                res = self.mapa(c["resultados"], f"{d} > resultados")
                del_yaml = set(res)
                usados: dict[str, dict[str, set]] = {}
                for ev, rr in res.items():
                    dr = f"{d} > resultados > {ev}"
                    rr = self.mapa(rr, dr, ["si", "desde", "a", "valores", "guarda"], ["si"])
                    # Lo que guarda y fija solo este resultado (además de lo del comando).
                    bolsa_r, propios_r = dict(bolsa), set(propios)
                    propios_r |= set(self.revisar_valores(rr.get("valores"), bolsa_r, f"{dr} > valores", todos))
                    guarda_r = self.lista(rr.get("guarda"), f"{dr} > guarda")
                    if guarda_r and m["acceso"] not in ESCRIBEN:
                        self.error(f"{dr} > guarda", f"el comando guarda datos pero en el modelo su acceso a la raíz es de {m['acceso']}")
                    guardados_r = self.revisar_guarda(guarda_r, bolsa_r, propios_r, f"{dr} > guarda", campos_raiz, vos, nombre_raiz)
                    bolsas_resultado[ev] = (bolsa_r, {**guardados, **guardados_r}, propios_r)
                    for campo, vals in self.condicion(rr.get("si"), bolsa, f"{dr} > si", propios).items():
                        for otro, vals_otro in usados.get(campo, {}).items():
                            if vals & vals_otro:
                                self.error(dr, f'su condición se cruza con la de "{otro}" en {sorted(vals & vals_otro)}')
                        usados.setdefault(campo, {})[ev] = vals
                    if "desde" in rr:
                        self.estados_validos(rr["desde"], f"{dr} > desde")
                    elif desde is None:
                        self.error(dr, "falta desde, en el resultado o en el comando")
                    if "a" in rr:
                        self.estados_validos(rr["a"], f"{dr} > a")
                        if lectura:
                            self.error(dr, "el comando solo lee la raíz: no puede cambiar el estado (a)")
                for campo, por_ev in usados.items():
                    t = bolsa.get(campo)
                    if t and t["enum"]:
                        falta = set(t["enum"]["valores"]) - set().union(*por_ev.values())
                        if falta:
                            self.aviso(d, f'ningún resultado cubre {sorted(falta)} de "{campo}"')
            for ev in sorted(del_modelo - del_yaml):
                self.error(d, f'en el modelo dispara "{ev}" y el YAML no lo declara')
            for ev in sorted(del_yaml - del_modelo):
                self.error(d, f'el YAML declara "{ev}" y en el modelo el comando no lo dispara')

            for ev in del_yaml & del_modelo:
                bolsa_e, guardados_e, propios_e = bolsas_resultado.get(ev, (bolsa, guardados, propios))
                bolsa_ev = dict(bolsa_e)
                self.agregar(bolsa_ev, guardados_e, d)
                if crea:                   # después de guardar ya hay identidad y estado
                    bolsa_ev.update(base)
                    if estado_t:
                        bolsa_ev["estado"] = estado_t
                bolsas_evento.setdefault(ev, []).append((n, bolsa_ev, frozenset(propios_e), self.rc["nombre"]))
        for nr in self.raices:
            if nr not in crean_por_raiz:
                self.error("comandos", f'ningún comando crea la raíz "{nr}" (crea: true o crea: si_no_existe)')
        for sa, info in sorted(sas.items()):
            if not info["usado_por"]:
                self.error("servicios_sa", f'ningún comando usa "{sa}" (V9-DEC-03)')

        # ---- eventos del contexto
        evs_y = self.mapa(s.get("eventos"), "eventos")
        self.cubre("eventos", evs_y, evs_m, "evento")
        datos_evento = {}
        for n in sorted(set(evs_y) & set(evs_m)):
            d = f"eventos > {n}"
            rc = self.raiz_por_agregado.get(evs_m[n]["agregado_id"])
            if rc:                                        # el evento lleva la identidad de la raíz de su agregado
                self.usar(rc)
            e = self.mapa(evs_y[n], d, ["datos", "calculados"], ["datos"])
            datos = self.campos(e.get("datos"), f"{d} > datos")
            calc = self.campos(e.get("calculados"), f"{d} > calculados")
            datos_evento[n] = {**datos, **calc}
            for cmd, bolsa, propios, nraiz in bolsas_evento.get(n, []):
                self.usar(self.raices[nraiz])
                self.pide(bolsa, datos, f"{d} > datos", f'el evento (publicado por "{cmd}")', propios)
                for k in calc:
                    if k in bolsa:
                        self.error(f"{d} > calculados", f'"{k}" ya está disponible en "{cmd}": va en datos')

        # ---- políticas internas: el evento debe traer lo que pide la entrada del comando que dispara
        cmd_por_id = {c["id"]: c["nombre"] for c in ctx["comandos"]}
        for p in ctx["politicas"]:
            ev, cmd = ev_por_id.get(p["evento_id"]), cmd_por_id.get(p["comando_id"])
            if ev not in datos_evento or cmd not in entradas_cmd:
                continue
            d = f'política "{ev}" dispara "{cmd}"'
            ev_m = next((e for e in ctx["eventos"] if e["nombre"] == ev), None)
            r_ev = self.raiz_por_agregado.get(ev_m["agregado_id"]) if ev_m else None
            r_cmd = self.raices.get(entradas_cmd[cmd]["raiz"])
            if r_ev and r_cmd and r_ev["id_nombre"] != r_cmd["id_nombre"]:
                self.error(d, f'el evento lleva "{r_ev["id_nombre"]}" y "{cmd}" necesita "{r_cmd["id_nombre"]}": '
                              "una política entre raíces con distinta identidad todavía no se genera")
            if entradas_cmd[cmd]["crea"]:
                self.error(d, f'"{cmd}" crea la raíz: un evento no puede dispararlo')
            for k, t in entradas_cmd[cmd]["entrada"].items():
                if k not in datos_evento[ev]:
                    if not t["opcional"]:
                        self.error(d, f'"{cmd}" necesita "{k}" y el evento no lo trae')
                elif not mismo_tipo(datos_evento[ev][k], t):
                    self.error(d, f'"{k}" llega como {datos_evento[ev][k]["tipo"]} y "{cmd}" lo espera como {t["tipo"]}')

        # ---- consultas
        qs_m = {q["nombre"]: q for q in ctx["consultas"]}
        qs_y = self.mapa(s.get("consultas"), "consultas")
        self.cubre("consultas", qs_y, qs_m, "consulta")
        for n in sorted(set(qs_y) & set(qs_m)):
            d = f"consultas > {n}"
            q = self.mapa(qs_y[n], d, ["entrada", "sobre", "de", "filtro", "filtro_manual", "salida", "agrega", "lista",
                                       "calculados"], ["entrada"])
            if "salida" not in q and "calculados" not in q:
                self.error(d, "debe tener salida o calculados")
            # La raíz de la consulta: la única que lee, o la que dice "de" (sobre cuál recorre, si lee varias).
            leidas = [self.raiz_por_id[x["raiz_id"]]["nombre"] for x in qs_m[n]["lee"] if x["raiz_id"] in self.raiz_por_id]
            if "de" in q:
                if "sobre" not in q:
                    self.error(f"{d} > de", "de solo va con sobre: todas")
                if q["de"] not in leidas:
                    self.error(f"{d} > de", f'"{q["de"]}" no es una raíz que la consulta lea en el modelo; lee: {", ".join(leidas)}')
                    continue
                nombre_q = q["de"]
            elif len(leidas) == 1:
                nombre_q = leidas[0]
            else:
                self.error(d, f'lee {len(leidas)} raíces ({", ".join(leidas)}): con sobre: todas, di con "de" sobre cuál recorre; '
                              "una consulta por identidad sobre varias raíces todavía no se genera (G5)")
                continue
            con_raiz, todos, *_ = self.usar(self.raices[nombre_q])
            if "sobre" in q:
                self.revisar_consulta_sobre_todas(q, d, con_raiz)
                continue
            for k in ("filtro", "filtro_manual", "agrega", "lista"):
                if k in q:
                    self.error(d, f"{k} solo va con sobre: todas")
            bolsa = dict(con_raiz)
            ent_q = self.campos(q.get("entrada"), f"{d} > entrada")
            self.agregar(bolsa, ent_q, f"{d} > entrada")
            for k in sorted(set(ent_q) & set(todos)):
                self.varios_origenes.append(f'{n}: "{k}" llega de raíz, entrada; se usa entrada')
            sal = self.campos(q.get("salida"), f"{d} > salida", libres=True)
            self.pide(bolsa, sal, f"{d} > salida", "la consulta")
            for k in self.campos(q.get("calculados"), f"{d} > calculados"):
                if k in bolsa:
                    self.error(f"{d} > calculados", f'"{k}" ya está disponible: va en salida')

        # ---- eventos de otros contextos
        catalogo = {}
        for o in ctx["otros_contextos"]:
            for e in o["eventos"]:
                catalogo.setdefault(e["nombre"], []).append(o["nombre"])
        ext = self.mapa(s.get("eventos_de_otros_contextos"), "eventos_de_otros_contextos")
        for n in sorted(ext):
            d = f"eventos_de_otros_contextos > {n}"
            x = self.mapa(ext[n], d, ["de", "identidad", "dispara", "con", "junto_con", "datos"], ["de", "datos"])
            if n in evs_m:
                self.error(d, "es un evento de este contexto, no de otro")
            elif n not in catalogo:
                self.error(d, f'"{n}" no existe en el modelo como evento de otro contexto')
            elif x.get("de") not in catalogo[n]:
                self.error(d, f'en el modelo "{n}" es de {", ".join(catalogo[n])}, no de "{x.get("de")}"')
            # La raíz del evento: la del comando que dispara; si no dispara y hay varias raíces, su identidad se escribe.
            cmd_d = x.get("dispara")
            if cmd_d in entradas_cmd:
                self.usar(self.raices[entradas_cmd[cmd_d]["raiz"]])
            elif "identidad" not in x and len(self.raices) > 1:
                self.error(f"{d} > identidad", "el contexto tiene varias raíces: di con qué dato llega el evento (identidad)")
            # identidad: el dato con que llega el evento (por defecto, la identidad de la raíz de este contexto).
            id_ev = x.get("identidad", self.id_nombre)
            if not isinstance(id_ev, str) or not id_ev.strip():
                self.error(f"{d} > identidad", "es el nombre del dato con que llega el evento")
            elif id_ev in (x.get("datos") or {}):
                self.error(f"{d} > datos", f'"{id_ev}" es la identidad del evento: se agrega sola')
            if "dispara" not in x:
                # Sin dispara, el evento solo se recuerda, para los comandos que lo requieren (requiere).
                for k in ("con", "junto_con"):
                    if k in x:
                        self.error(d, f"{k} solo va con dispara")
                if n not in self.requeridos:
                    self.error(d, "no dispara ningún comando y ningún comando lo requiere (requiere): nadie lo usa")
                self.campos(x.get("datos"), f"{d} > datos")
                continue
            cmd = x.get("dispara")
            otra_identidad = id_ev != self.id_nombre      # G3: la identidad de la raíz sale de los datos, por su nombre
            if otra_identidad and self.id_nombre not in (x.get("datos") or {}):
                self.error(f"{d} > datos", f'llega con "{id_ev}" y dispara "{cmd}": debe traer "{self.id_nombre}", la identidad de la raíz')
            if cmd not in entradas_cmd:
                self.error(d, f'dispara "{cmd}", que no es un comando especificado del contexto')
                continue
            if entradas_cmd[cmd]["crea"]:
                self.error(d, f'"{cmd}" crea la raíz: un evento de otro contexto no puede dispararlo')
            ent = entradas_cmd[cmd]["entrada"]
            aporta = {}
            self.agregar(aporta, self.campos(x.get("datos"), f"{d} > datos", permitidos=(self.id_nombre,) if otra_identidad else ()),
                         f"{d} > datos")
            if otra_identidad:                            # la identidad del evento también le sirve al comando
                aporta.pop(self.id_nombre, None)
                aporta.setdefault(id_ev, tipos.interpretar("string"))
            for k, v in self.mapa(x.get("con"), f"{d} > con").items():
                if k not in ent:
                    self.error(f"{d} > con", f'"{k}" no está en la entrada de "{cmd}"')
                elif not valor_valido(v, ent[k]):
                    self.error(f"{d} > con", f'el valor {v!r} no es válido para "{k}" ({ent[k]["tipo"]})')
                else:
                    aporta[k] = ent[k]
            for otro in self.lista(x.get("junto_con"), f"{d} > junto_con"):
                o = ext.get(otro) if isinstance(ext.get(otro), dict) else None
                if o is None:
                    self.error(f"{d} > junto_con", f'"{otro}" no está en esta sección')
                    continue
                if o.get("dispara") != cmd or n not in (o.get("junto_con") or []):
                    self.error(f"{d} > junto_con", f'"{otro}" debe disparar "{cmd}" y nombrar a "{n}" en su junto_con')
                for k, t in (o.get("datos") or {}).items():
                    try:
                        aporta.setdefault(k, tipos.interpretar(t))
                    except tipos.TipoInvalido:
                        pass
            for k, t in aporta.items():
                if k in ent and not mismo_tipo(ent[k], t):
                    self.error(d, f'"{k}" llega como {t["tipo"]} y "{cmd}" lo espera como {ent[k]["tipo"]}')
                elif k not in ent:
                    self.aviso(d, f'"{k}" no está en la entrada de "{cmd}": el comando no lo usa')
            for k, t in ent.items():
                if not t["opcional"] and k not in aporta:
                    self.error(d, f'"{cmd}" necesita "{k}" y ni el evento ni junto_con ni con lo traen')

        # ---- escenarios: solo se revisa que estén bien escritos (no se simulan los datos)
        self.revisar_escenarios(s, ctx, entradas_cmd, crean, ext, qs_y, ev_por_id)

    AGREGACIONES = ("promedio", "suma", "mínimo", "máximo")

    def interpretar_agregado(self, texto, con_raiz: dict, donde: str):
        """ "conteo" o "<promedio|suma|mínimo|máximo> de <dato de la raíz>". Devuelve (función, dato o None)."""
        if texto == "conteo":
            return "conteo", None
        if isinstance(texto, str):
            for f in self.AGREGACIONES:
                if texto.startswith(f + " de "):
                    dato = texto[len(f) + 4:].strip()
                    if dato not in con_raiz:
                        self.error(donde, f'"{dato}" no es un dato de la raíz')
                        return None
                    return f, dato
        self.error(donde, f'{texto!r} no es una agregación; se escribe "conteo" o "<{"|".join(self.AGREGACIONES)}> de <dato>"')
        return None

    def revisar_consulta_sobre_todas(self, q: dict, d: str, con_raiz: dict):
        """Consulta sobre todas las instancias de la raíz (G5): filtra por igualdad con datos de su entrada y
        devuelve agregaciones (conteo, promedio, suma, mínimo, máximo)."""
        if q.get("sobre") != "todas":
            self.error(f"{d} > sobre", 'por ahora solo se permite "sobre: todas"')
            return
        ent = self.campos(q.get("entrada"), f"{d} > entrada")
        for dato in self.lista(q.get("filtro"), f"{d} > filtro"):
            if dato not in ent:
                self.error(f"{d} > filtro", f'"{dato}" no está en la entrada de la consulta')
            elif dato not in con_raiz:
                self.error(f"{d} > filtro", f'"{dato}" no es un dato de la raíz: no hay con qué compararlo')
            elif not mismo_tipo(ent[dato], con_raiz[dato]):
                self.error(f"{d} > filtro", f'"{dato}" llega como {ent[dato]["tipo"]} y en la raíz es {con_raiz[dato]["tipo"]}')
        if q.get("filtro_manual", False) not in (True, False):
            self.error(f"{d} > filtro_manual", "es true o false")
        sal = self.campos(q.get("salida"), f"{d} > salida", libres=True)
        if "agrega" not in q:
            # Sin agregaciones, la consulta devuelve una lista: un elemento por raíz, con los datos de la salida.
            if not isinstance(q.get("lista"), str) or not q["lista"].strip():
                self.error(d, "sin agrega, la consulta devuelve una lista: di su nombre con lista (por ejemplo, lista: yates disponibles)")
            self.pide(con_raiz, sal, f"{d} > salida", "un elemento de la lista")
            return
        if "lista" in q:
            self.error(f"{d} > lista", "con agrega la consulta devuelve agregaciones, no una lista")
        agrega = self.mapa(q.get("agrega"), f"{d} > agrega")
        for k in sorted(set(sal) - set(agrega)):
            self.error(f"{d} > agrega", f'falta cómo se calcula "{k}": en una consulta sobre todas, cada dato de la salida es una agregación')
        for k in sorted(set(agrega) - set(sal)):
            self.error(f"{d} > agrega", f'"{k}" no está en la salida')
        for k in sorted(set(sal) & set(agrega)):
            res = self.interpretar_agregado(agrega[k], con_raiz, f"{d} > agrega > {k}")
            if not res:
                continue
            f, dato = res
            ts = sal[k]
            if f == "conteo":
                if ts["base"] != "int" or ts["lista"]:
                    self.error(f"{d} > salida > {k}", "un conteo es int")
                continue
            tc = con_raiz[dato]
            if tc["lista"] or tc["opcional"]:
                self.error(f"{d} > agrega > {k}", f'"{dato}" debe ser un dato obligatorio y no una lista')
            elif f in ("promedio", "suma") and tc["base"] not in ("int", "decimal"):
                self.error(f"{d} > agrega > {k}", f'el {f} es de números; "{dato}" es {tc["tipo"]}')
            elif f in ("mínimo", "máximo") and tc["base"] not in ("int", "decimal", "DateOnly", "DateTime"):
                self.error(f"{d} > agrega > {k}", f'el {f} es de números o fechas; "{dato}" es {tc["tipo"]}')
            esperado = "decimal" if f == "promedio" else tc["base"]
            if ts["base"] != esperado or ts["lista"]:
                self.error(f"{d} > salida > {k}", f"el {f} de \"{dato}\" es {esperado}")
            if f != "suma" and not ts["opcional"]:
                self.error(f"{d} > salida > {k}", f"sin instancias no hay {f}: escribe {esperado}?")

    def revisar_escenarios(self, s, ctx, entradas_cmd, crean, ext, qs_y, ev_por_id):
        if "escenarios" not in s:
            return
        esc = self.mapa(s.get("escenarios"), "escenarios")
        cmd_por_id = {c["id"]: c["nombre"] for c in ctx["comandos"]}
        eventos_de = {c["nombre"]: {ev_por_id[i] for i in c["eventos"]} for c in ctx["comandos"]}
        politica = {}                                  # evento -> comandos que dispara (políticas internas)
        for p in ctx["politicas"]:
            politica.setdefault(ev_por_id.get(p["evento_id"]), []).append(cmd_por_id.get(p["comando_id"]))

        def alcanzables(cmd, vistos=None):
            """Eventos que publica el comando, directo o por las políticas que disparan sus eventos."""
            vistos = vistos or set()
            if cmd in vistos:
                return set()
            vistos.add(cmd)
            out = set(eventos_de.get(cmd, set()))
            for e in list(out):
                for otro in politica.get(e, []):
                    out |= alcanzables(otro, vistos)
            return out

        codigos = {"comando": {404, 409, 422}, "consulta": {404, 422}, "evento de otro contexto": {202, 404, 409, 422}}
        llamados = set()
        for nombre_e, pasos in esc.items():
            d = f"escenarios > {nombre_e}"
            pasos = self.lista(pasos, d)
            if not pasos:
                self.error(d, "el escenario no tiene pasos")
            for i, paso in enumerate(pasos, 1):
                dp = f"{d} > paso {i}"
                if isinstance(paso, str):
                    nombre, op = paso, {}
                elif isinstance(paso, dict) and len(paso) == 1:
                    nombre, op = next(iter(paso.items()))
                    op = self.mapa(op, f"{dp} ({nombre})", ["con", "espera"])
                else:
                    self.error(dp, 'un paso es un nombre, o "nombre:" con con y espera')
                    continue
                llamados.add(nombre)
                dp = f"{dp} ({nombre})"
                if nombre in entradas_cmd:
                    tipo, campos = "comando", dict(entradas_cmd[nombre]["entrada"])
                    if not entradas_cmd[nombre]["crea"]:  # la identidad de su raíz puede ir en con
                        campos.setdefault(self.raices[entradas_cmd[nombre]["raiz"]]["id_nombre"], tipos.interpretar("string"))
                elif nombre in qs_y:
                    tipo = "consulta"
                    campos = {k: tipos.interpretar(v) for k, v in ((qs_y[nombre] or {}).get("entrada") or {}).items()}
                elif nombre in ext:
                    tipo = "evento de otro contexto"
                    x = ext[nombre] or {}
                    campos = {k: tipos.interpretar(v) for k, v in (x.get("datos") or {}).items()}
                    if x.get("identidad", self.id_nombre) != self.id_nombre:   # su identidad no es la de la raíz: va en con
                        campos[x["identidad"]] = tipos.interpretar("string")
                else:
                    self.error(dp, f'"{nombre}" no es un comando, una consulta ni un evento de otro contexto del YAML')
                    continue
                for k, v in self.mapa(op.get("con"), f"{dp} > con").items():
                    if k not in campos:
                        self.error(f"{dp} > con", f'"{k}" no está en la entrada (o en los datos) de "{nombre}"')
                    elif not valor_valido(v, campos[k]):
                        self.error(f"{dp} > con", f'el valor {v!r} no es válido para "{k}" ({campos[k]["tipo"]})')
                if "espera" not in op:
                    continue
                esp = op["espera"]
                if isinstance(esp, bool):
                    self.error(f"{dp} > espera", "espera no puede ser true o false")
                elif isinstance(esp, int):
                    if esp not in codigos[tipo]:
                        self.error(f"{dp} > espera", f"el código {esp} no se permite en un {tipo}; se permiten {sorted(codigos[tipo])}")
                elif isinstance(esp, str):
                    if tipo == "consulta":
                        self.error(f"{dp} > espera", "una consulta no publica eventos; usa espera: {estado: ...} o un código")
                    else:
                        cmd = nombre if tipo == "comando" else (ext[nombre] or {}).get("dispara")
                        posibles = alcanzables(cmd)
                        if esp not in posibles:
                            self.error(f"{dp} > espera", f'"{esp}" no es un evento que publique "{cmd}" (directo o por una política); '
                                                         f'posibles: {", ".join(sorted(posibles))}')
                elif isinstance(esp, dict):
                    if tipo != "consulta":
                        self.error(f"{dp} > espera", "espera: {dato: valor, ...} solo va en una consulta")
                    else:
                        qy = qs_y[nombre] or {}
                        salida_q = {}
                        for k, v in {**(qy.get("salida") or {}), **(qy.get("calculados") or {})}.items():
                            try:
                                salida_q[k] = tipos.interpretar(v)
                            except tipos.TipoInvalido:
                                pass
                        if isinstance(qy.get("lista"), str):     # una lista se compara por cuántos elementos tiene
                            salida_q = {qy["lista"]: tipos.interpretar("int")}
                        if not esp:
                            self.error(f"{dp} > espera", "di qué datos de la salida se esperan")
                        for k, v in esp.items():
                            if k not in salida_q:
                                self.error(f"{dp} > espera", f'"{k}" no está en la salida de "{nombre}"')
                            elif k == "estado" and salida_q[k]["base"] == "enum" and salida_q[k]["enum"]["valores"] == self.estados:
                                self.estados_validos(v, f"{dp} > espera > estado")
                            elif not valor_valido(v, salida_q[k]):
                                self.error(f"{dp} > espera", f'el valor {v!r} no es válido para "{k}" ({salida_q[k]["tipo"]})')
                else:
                    self.error(f"{dp} > espera", "espera es un evento, un código HTTP o {dato de la salida: valor, ...}")
        for n in sorted((set(entradas_cmd) | set(qs_y) | set(ext)) - llamados):
            self.aviso("escenarios", f'"{n}" no aparece en ningún escenario: pruebas.http no lo llamará')

    def resumen(self) -> list[str]:
        s = self.s
        texto = Path(self.archivo).read_text(encoding="utf-8")
        n_sup = sum(1 for linea in texto.splitlines() if "# supuesto" in linea and '"# supuesto"' not in linea)
        return [f'{s["contexto"]}: {len(s["raices"])} raíz, {len(s["comandos"])} comandos, {len(s["eventos"])} eventos, '
                f'{len(s["consultas"])} consultas, {len(s.get("eventos_de_otros_contextos") or {})} eventos de otros '
                f'contextos, {len(s["servicios_sa"])} servicios SA, {len(s.get("escenarios") or {})} escenarios; {len(self.enums)} enums; '
                f'{n_sup} líneas con "# supuesto".']


def main():
    for f in (sys.stdout, sys.stderr):
        f.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    ruta_json, ruta_yaml = sys.argv[1:]
    modelo = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
    try:
        spec = cargar_yaml(ruta_yaml)
    except yaml.YAMLError as e:
        sys.exit(f"ERROR al leer {ruta_yaml}: {e}")
    rev = Revisor(modelo, spec, ruta_yaml)
    rev.id_nombre = ""
    rev.revisar()
    for a in rev.avisos:
        print("AVISO", a)
    if rev.varios_origenes:
        print("Datos que llegan de más de un origen (gana el más reciente: SA, luego entrada, luego raíz):")
        for v in rev.varios_origenes:
            print("  -", v)
    if rev.errores:
        print(f"\n{len(rev.errores)} error(es) en {ruta_yaml}:", file=sys.stderr)
        for e in rev.errores:
            print("  ERROR", e, file=sys.stderr)
        sys.exit(1)
    print("\n".join(rev.resumen()))
    print(f"\nEl YAML cumple con el modelo: {ruta_yaml}")


if __name__ == "__main__":
    main()
