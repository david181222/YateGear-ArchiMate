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

    def campos(self, x, donde: str, libres: bool = False) -> dict[str, dict]:
        """Datos "nombre: tipo". La identidad y el estado se agregan solos, así que solo se
        pueden escribir donde se piden o se devuelven (libres=True): entrada de un SA y salida de una consulta."""
        out = {}
        for nombre, texto in self.mapa(x, donde).items():
            if not isinstance(nombre, str) or not nombre.strip():
                self.error(donde, f"nombre de dato vacío o inválido: {nombre!r}")
                continue
            if not libres and nombre in (self.id_nombre, "estado"):
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
        if len(raices_m) != 1:
            self.error("raices", "el piloto admite un solo agregado por contexto")
            return
        nombre_raiz = next(iter(raices_m))
        ag = agregados[raices_m[nombre_raiz]["id"]]
        r = self.mapa(raices_y.get(nombre_raiz), f"raices > {nombre_raiz}", ["identidad", "estado"], ["identidad", "estado"])
        ident = self.mapa(r.get("identidad"), f"raices > {nombre_raiz} > identidad",
                          ["nombre", "tipo", "prefijo", "digitos"], ["nombre", "tipo", "prefijo", "digitos"])
        self.id_nombre = ident.get("nombre", "")
        self.id_tipo = self.tipo(ident.get("tipo"), f"raices > {nombre_raiz} > identidad > tipo")
        if self.id_tipo and (self.id_tipo["base"] != "string" or self.id_tipo["lista"] or self.id_tipo["opcional"]):
            self.error(f"raices > {nombre_raiz} > identidad", "la identidad debe ser string obligatorio: es el consecutivo con prefijo")
        if not isinstance(ident.get("digitos"), int) or isinstance(ident.get("digitos"), bool) or ident.get("digitos", 0) < 1:
            self.error(f"raices > {nombre_raiz} > identidad", "digitos debe ser un entero mayor que 0")
        estado_t = self.tipo(r.get("estado"), f"raices > {nombre_raiz} > estado")
        if estado_t and (estado_t["base"] != "enum" or estado_t["opcional"]):
            self.error(f"raices > {nombre_raiz} > estado", "el estado debe ser un enum obligatorio")
            estado_t = None
        self.estados = estado_t["enum"]["valores"] if estado_t else []

        # Campos de la raíz y de sus objetos de valor. Un nombre que está en dos de ellos es ambiguo:
        # solo es error si un comando, evento o consulta lo usa sin que llegue por su entrada o por un SA.
        campos_raiz = {c["nombre"]: c for c in ag["raiz"]["campos"]}
        vos = {v["nombre"]: v for v in ag["objetos_valor"] + ag["entidades"]}
        todos, origenes = {}, {}
        for dueno, lista in [(nombre_raiz, ag["raiz"]["campos"])] + [(v["nombre"], v["campos"]) for v in vos.values()]:
            for c in lista:
                if c["nombre"] in (self.id_nombre, "estado"):
                    self.error("modelo", f'el campo "{c["nombre"]}" de "{dueno}" se llama igual que la identidad o el estado')
                origenes.setdefault(c["nombre"], []).append(f'"{dueno}"')
                todos.setdefault(c["nombre"], c)
        self.ambiguos = {n: l for n, l in origenes.items() if len(l) > 1}
        base = {self.id_nombre: self.id_tipo} if self.id_tipo else {}
        con_raiz = {**base, **todos, **({"estado": estado_t} if estado_t else {})}

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
        for n in sorted(set(cmds_y) & set(cmds_m)):
            d = f"comandos > {n}"
            m = cmds_m[n]
            c = self.mapa(cmds_y[n], d, ["crea", "desde", "a", "entrada", "usa", "guarda", "eventos", "resultados"], ["entrada"])
            crea = c.get("crea", False)
            if crea not in (True, False):
                self.error(d, "crea debe ser true o false")
                crea = False
            if crea:
                crean.append(n)
                if m["acceso"] not in ESCRIBEN:
                    self.error(d, f"el comando crea la raíz pero en el modelo su acceso es de {m['acceso']}")
            ent = self.campos(c.get("entrada"), f"{d} > entrada")
            entradas_cmd[n] = {"entrada": ent, "crea": crea}
            # El comando que crea la raíz no tiene raíz ni identidad hasta que la guarda (la identidad se
            # asigna al guardar, después de ValidarReglas): sus SA y condiciones solo usan entrada y SA.
            bolsa = {} if crea else dict(con_raiz)
            self.agregar(bolsa, ent, f"{d} > entrada")
            propios = set(ent)
            origenes_cmd = {} if crea else {k: ["raíz"] for k in todos}
            for k in ent:
                origenes_cmd.setdefault(k, []).append("entrada")

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
            guardados, destinos = {}, {}
            guarda = self.lista(c.get("guarda"), f"{d} > guarda")
            if guarda and m["acceso"] not in ESCRIBEN:
                self.error(f"{d} > guarda", f"el comando guarda datos pero en el modelo su acceso a la raíz es de {m['acceso']}")
            for g in guarda:
                if g in vos:
                    v = vos[g]
                    if v["cardinalidad"] == "Muchos":
                        self.error(f"{d} > guarda", f'"{g}" tiene Cardinalidad Muchos; el piloto todavía no la guarda')
                    for campo in v["campos"]:
                        if campo["nombre"] in bolsa or not campo["opcional"]:
                            self.pide(bolsa, {campo["nombre"]: campo}, f"{d} > guarda", f'el objeto de valor "{g}"', propios)
                        guardados[campo["nombre"]] = campo
                        destinos.setdefault(campo["nombre"], []).append(f'"{g}"')
                elif g in campos_raiz:
                    self.pide(bolsa, {g: campos_raiz[g]}, f"{d} > guarda", f'el campo "{g}" de la raíz', propios)
                    guardados[g] = campos_raiz[g]
                    destinos.setdefault(g, []).append(f'la raíz "{nombre_raiz}"')
                else:
                    self.error(f"{d} > guarda", f'"{g}" no es un objeto de valor ni un campo de la raíz {nombre_raiz}')
            for nombre_dato, lugares in sorted(destinos.items()):
                if len(lugares) > 1:
                    self.error(f"{d} > guarda", f'"{nombre_dato}" puede ir a más de un destino: {" y ".join(lugares)}')
            if crea:
                for v in vos.values():
                    if v["cardinalidad"] == "Uno" and v["nombre"] not in guarda:
                        self.error(f"{d} > guarda", f'crea la raíz y no guarda "{v["nombre"]}", que tiene Cardinalidad Uno')
                for campo in campos_raiz.values():
                    if not campo["opcional"] and campo["nombre"] not in guarda:
                        self.error(f"{d} > guarda", f'crea la raíz y no guarda su campo obligatorio "{campo["nombre"]}"')

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
                    rr = self.mapa(rr, dr, ["si", "desde", "a"], ["si"])
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

            bolsa_ev = dict(bolsa)
            self.agregar(bolsa_ev, guardados, d)
            if crea:                       # después de guardar ya hay identidad y estado
                bolsa_ev.update(base)
                if estado_t:
                    bolsa_ev["estado"] = estado_t
            for ev in del_yaml & del_modelo:
                bolsas_evento.setdefault(ev, []).append((n, bolsa_ev, frozenset(propios)))
        if not crean:
            self.error("comandos", f'ningún comando crea la raíz "{nombre_raiz}" (crea: true)')
        for sa, info in sorted(sas.items()):
            if not info["usado_por"]:
                self.error("servicios_sa", f'ningún comando usa "{sa}" (V9-DEC-03)')

        # ---- eventos del contexto
        evs_y = self.mapa(s.get("eventos"), "eventos")
        self.cubre("eventos", evs_y, evs_m, "evento")
        datos_evento = {}
        for n in sorted(set(evs_y) & set(evs_m)):
            d = f"eventos > {n}"
            e = self.mapa(evs_y[n], d, ["datos", "calculados"], ["datos"])
            datos = self.campos(e.get("datos"), f"{d} > datos")
            calc = self.campos(e.get("calculados"), f"{d} > calculados")
            datos_evento[n] = {**datos, **calc}
            for cmd, bolsa, propios in bolsas_evento.get(n, []):
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
            q = self.mapa(qs_y[n], d, ["entrada", "salida", "calculados"], ["entrada"])
            if "salida" not in q and "calculados" not in q:
                self.error(d, "debe tener salida o calculados")
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
            x = self.mapa(ext[n], d, ["de", "dispara", "con", "junto_con", "datos"], ["de", "dispara", "datos"])
            if n in evs_m:
                self.error(d, "es un evento de este contexto, no de otro")
            elif n not in catalogo:
                self.error(d, f'"{n}" no existe en el modelo como evento de otro contexto')
            elif x.get("de") not in catalogo[n]:
                self.error(d, f'en el modelo "{n}" es de {", ".join(catalogo[n])}, no de "{x.get("de")}"')
            cmd = x.get("dispara")
            if cmd not in entradas_cmd:
                self.error(d, f'dispara "{cmd}", que no es un comando especificado del contexto')
                continue
            if entradas_cmd[cmd]["crea"]:
                self.error(d, f'"{cmd}" crea la raíz: un evento de otro contexto no puede dispararlo')
            ent = entradas_cmd[cmd]["entrada"]
            aporta = {}
            self.agregar(aporta, self.campos(x.get("datos"), f"{d} > datos"), f"{d} > datos")
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
        crea = crean[0] if crean else None
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
                    tipo, campos = "comando", entradas_cmd[nombre]["entrada"]
                elif nombre in qs_y:
                    tipo = "consulta"
                    campos = {k: tipos.interpretar(v) for k, v in ((qs_y[nombre] or {}).get("entrada") or {}).items()}
                elif nombre in ext:
                    tipo = "evento de otro contexto"
                    campos = {k: tipos.interpretar(v) for k, v in ((ext[nombre] or {}).get("datos") or {}).items()}
                else:
                    self.error(dp, f'"{nombre}" no es un comando, una consulta ni un evento de otro contexto del YAML')
                    continue
                if i == 1 and nombre != crea:
                    self.error(dp, f'el primer paso debe ser "{crea}", para que el escenario tenga su propio arriendo')
                if i > 1 and nombre == crea:
                    self.error(dp, f'"{crea}" solo va como primer paso: cada escenario tiene un solo arriendo')
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
                    if i == 1:
                        self.error(f"{dp} > espera", "el primer paso crea el arriendo del escenario y debe responder con éxito")
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
                    esp = self.mapa(esp, f"{dp} > espera", ["estado"], ["estado"])
                    if tipo != "consulta":
                        self.error(f"{dp} > espera", "espera: {estado: ...} solo va en una consulta")
                    elif "estado" in esp:
                        self.estados_validos(esp["estado"], f"{dp} > espera > estado")
                else:
                    self.error(f"{dp} > espera", "espera es un evento, un código HTTP o {estado: ...}")
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
