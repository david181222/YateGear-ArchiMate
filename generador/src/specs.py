"""Revisa el YAML de especificaciones de un contexto contra modelo-ddd.json.

No genera nada. Junta todos los errores y termina con código 1 si el YAML:
  - deja sin especificar un elemento del contexto o nombra uno que no existe;
  - tiene una clave desconocida o repetida, un tipo no permitido o un estado
    fuera de la lista cerrada;
  - declara para un comando eventos distintos de los que ese comando dispara
    en el modelo (ni más ni menos);
  - usa un dato que no está disponible por su nombre, con el mismo tipo, donde
    se necesita (regla de los datos, ver el comentario al inicio del YAML).

Además revisa los contratos entre contextos (revisar_contratos, D2) contra los YAML de los demás contextos de su
misma carpeta: lo que el YAML declara que recibe de otro contexto debe llegar, con el mismo tipo, en el evento que ese
contexto publica; y lo que publica debe cubrir lo que los demás declaran recibir de él.

Un YAML de escenarios entre contextos (S4, solo con escenarios_entre_contextos) se revisa contra los YAML de
los contextos de su misma carpeta.

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
# Campos de una respuesta de error que un escenario puede afirmar (espera: {código: ..., campo: valor}), y su nombre en JSON.
CAMPOS_DE_ERROR = {"regla": "regla", "requiere": "requiere", "identidad": "identidad", "operación": "operacion",
                   "estado actual": "estadoActual"}


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
    return a["base"] == b["base"] and a["lista"] == b["lista"] and a["enum"] == b["enum"] and a.get("objeto") == b.get("objeto")


def opcional(t: dict) -> dict:
    """El mismo tipo, opcional (con ?)."""
    return t if t["opcional"] else {**t, "opcional": True, "tipo": t["tipo"] + "?"}


def valor_valido(v, t: dict) -> bool:
    if v is None:
        return t["opcional"]
    if t["lista"]:
        uno = {**t, "lista": False, "opcional": False}
        return isinstance(v, list) and all(valor_valido(x, uno) for x in v)
    b = t["base"]
    if b == "objeto":                     # un elemento de List<objeto de valor>: {campo: valor, ...}
        campos = tipos.OBJETOS.get(t["objeto"], {})
        return isinstance(v, dict) and set(v) <= set(campos) and all(
            (k in v and valor_valido(v[k], ct)) or (k not in v and ct["opcional"]) for k, ct in campos.items())
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


OPCIONES_DISPARO = ("con", "correspondencias", "si", "salvo", "si_existe")
OPCIONES_USO_SA = ("con", "entrada", "salida", "si", "salvo")


def disparos(x: dict) -> list[tuple[str, dict]]:
    """Los comandos que dispara un evento de otro contexto o un mensaje de un SA, en orden, con sus opciones.

    dispara puede ser un nombre (las opciones con y correspondencias van junto a dispara), una lista de nombres o
    {comando: {con, correspondencias, si, salvo, si_existe}, ...}. Un nombre o un elemento que no es texto se devuelve igual,
    para que el revisor diga cuál está mal.
    """
    d = x.get("dispara")
    if isinstance(d, str):
        return [(d, {k: x[k] for k in ("con", "correspondencias") if k in x})]
    if isinstance(d, list):
        return [(c, {}) for c in d]
    if isinstance(d, dict):
        return [(c, op if isinstance(op, dict) else {}) for c, op in d.items()]
    return []


def uso_sa(item) -> tuple[str, dict]:
    """Un elemento de usa: el nombre del SA, o {SA: {con, entrada, salida, si, salvo}}."""
    if isinstance(item, dict) and len(item) == 1:
        nombre, op = next(iter(item.items()))
        return nombre, op if isinstance(op, dict) else {}
    return item, {}


def ubicar_calculados(de: dict[str, list[str]], al_inicio: set, salidas: list[set]) -> list[list[str]]:
    """Dónde se calcula cada dato calculado de un comando: en cuanto están los datos de los que sale.

    de: calculado -> datos de los que sale (en el orden del YAML). al_inicio: lo disponible antes de llamar a los SA
    (entrada, raíz, valores, eventos requeridos, otras raíces). salidas: lo que deja cada llamada a un SA, en orden.
    Devuelve, para cada punto (0 = antes de la primera llamada, i = después de la llamada i), los calculados que se
    calculan ahí, en el orden del YAML. Los que nunca tienen sus datos quedan en el último punto con una marca: el
    revisor los informa.
    """
    disponibles, pendientes, puntos = set(al_inicio), list(de), []
    for i in range(len(salidas) + 1):
        if i > 0:
            disponibles |= salidas[i - 1]
        aqui, avanza = [], True
        while avanza:
            avanza = False
            for c in list(pendientes):
                if all(x in disponibles for x in de[c]):
                    aqui.append(c)
                    pendientes.remove(c)
                    disponibles.add(c)
                    avanza = True
        puntos.append(aqui)
    if pendientes:
        puntos[-1] += [None] + pendientes             # None separa los que no se pueden calcular
    return puntos


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

    def si_salvo(self, x: dict, bolsa: dict, donde: str, propios=frozenset()):
        """Condiciones si (el dato está entre esos valores) y salvo (no está entre ellos) sobre los datos disponibles."""
        for k in ("si", "salvo"):
            if k in x:
                self.condicion(x[k], bolsa, f"{donde} > {k}", propios)

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

    def revisar_temporizador(self, x, ent: dict, d: str):
        """temporizador: {cada minutos: N, con: {dato: valor}, ahora: dato}. El comando corre solo cada N minutos con
        los valores de con y la hora actual en el dato de ahora; todo dato obligatorio de su entrada debe quedar cubierto."""
        x = self.mapa(x, d, ["cada minutos", "con", "ahora"], ["cada minutos"])
        cada = x.get("cada minutos")
        if not isinstance(cada, int) or isinstance(cada, bool) or cada < 1:
            self.error(d, "cada minutos es un entero mayor que 0")
        cubiertos = set()
        for k, v in self.mapa(x.get("con"), f"{d} > con").items():
            if k not in ent:
                self.error(f"{d} > con", f'"{k}" no está en la entrada del comando')
            elif not valor_valido(v, ent[k]):
                self.error(f"{d} > con", f'el valor {v!r} no es válido para "{k}" ({ent[k]["tipo"]})')
            cubiertos.add(k)
        if "ahora" in x:
            ahora = x["ahora"]
            if ahora not in ent or ent[ahora]["base"] != "DateTime" or ent[ahora]["lista"]:
                self.error(f"{d} > ahora", f'"{ahora}" debe ser un dato DateTime de la entrada')
            cubiertos.add(ahora)
        for k, t in ent.items():
            if not t["opcional"] and k not in cubiertos:
                self.error(d, f'el comando necesita "{k}" y el temporizador no lo da (con o ahora)')

    OPERACIONES_LISTA = ("agregar", "reemplazar", "quitar")

    def revisar_guarda(self, guarda: list, bolsa: dict, propios: set, d: str, campos_raiz: dict, vos: dict,
                       nombre_raiz: str) -> dict:
        """Lo que se guarda en la raíz: objetos de valor y campos por su nombre, {campo: dato} para guardar un dato
        con otro nombre, y en un objeto de valor con Cardinalidad Muchos (G4) {lista: agregar}, {lista: {reemplazar:
        [claves]}} o {lista: {quitar: [claves]}}. Cada dato debe tener un solo destino. Devuelve lo guardado."""
        guardados, destinos = {}, {}

        def pedir_vo(v, solo=None, cubiertos=frozenset()):
            for campo in v["campos"]:
                if solo is not None and campo["nombre"] not in solo or campo["nombre"] in cubiertos:
                    continue
                # Una lista que el comando no tiene queda vacía; un dato opcional que no tiene, en null.
                vacio = campo["opcional"] or tipos.interpretar(campo["tipo"])["lista"]
                if campo["nombre"] in bolsa or not vacio or solo is not None:
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
                elif isinstance(op, dict) and "agregar" in op:
                    # {lista: {agregar: {campo: dato}, valores: {campo: valor}, si: ..., salvo: ...}}: agrega un elemento
                    # con datos de otro nombre y valores fijos, y solo si se cumple la condición. Puede repetirse.
                    self.revisar_agregar(op, v, bolsa, propios, f"{d} > {nombre_vo}", pedir_vo)
                    for campo in v["campos"]:
                        guardados[campo["nombre"]] = campo
                    continue
                elif isinstance(op, dict) and len(op) == 1 and next(iter(op)) == "todos":
                    # {lista: {todos: dato}}: la lista entera se reemplaza con un dato de tipo List<objeto de valor>.
                    dato = op["todos"]
                    if not isinstance(dato, str) or dato not in bolsa:
                        self.error(d, f'"{nombre_vo}" se guarda entera con "{dato}", que el comando no tiene')
                    elif bolsa[dato].get("objeto") != nombre_vo or not bolsa[dato]["lista"]:
                        self.error(d, f'"{dato}" es {bolsa[dato]["tipo"]}; para guardar "{nombre_vo}" entera debe ser List<{nombre_vo}>')
                    destinos.setdefault(nombre_vo, []).append("todos")
                    continue
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
                    self.error(d, f'en "{nombre_vo}" (una lista) se escribe agregar, {{agregar: {{campo: dato}}, valores: ...}}, '
                                  f'{{reemplazar: [claves]}}, {{quitar: [claves]}} o {{todos: dato}}')
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

    def revisar_agregar(self, op: dict, v: dict, bolsa: dict, propios: set, d: str, pedir_vo):
        """{agregar: {campo: dato}, valores: {campo: valor}, si, salvo}: cada campo sale de una correspondencia, de un
        valor fijo o del dato con su nombre."""
        op = self.mapa(op, d, ["agregar", "valores", "si", "salvo"], ["agregar"])
        campos = {c["nombre"]: c for c in v["campos"]}
        cubiertos = set()
        for campo, dato in self.mapa(op.get("agregar"), f"{d} > agregar").items():
            if campo not in campos:
                self.error(f"{d} > agregar", f'"{campo}" no es un campo de "{v["nombre"]}"')
            elif not isinstance(dato, str) or dato not in bolsa:
                self.error(f"{d} > agregar", f'"{campo}" se guarda con "{dato}", que el comando no tiene')
            elif not mismo_tipo(bolsa[dato], tipos.interpretar(campos[campo]["tipo"])):
                self.error(f"{d} > agregar", f'"{dato}" es {bolsa[dato]["tipo"]} y "{campo}" es {campos[campo]["tipo"]}')
            cubiertos.add(campo)
        for campo, valor in self.mapa(op.get("valores"), f"{d} > valores").items():
            if campo not in campos:
                self.error(f"{d} > valores", f'"{campo}" no es un campo de "{v["nombre"]}"')
            elif campo in cubiertos:
                self.error(f"{d} > valores", f'"{campo}" ya tiene una correspondencia en agregar')
            elif not valor_valido(valor, tipos.interpretar(campos[campo]["tipo"])):
                self.error(f"{d} > valores", f'el valor {valor!r} no es válido para "{campo}" ({campos[campo]["tipo"]})')
            cubiertos.add(campo)
        self.si_salvo(op, bolsa, d, propios)
        pedir_vo(v, cubiertos=frozenset(cubiertos))

    def revisar_disparo(self, cmd: str, op: dict, aporta: dict, llegan: dict, entradas_cmd: dict, d: str, quien: str) -> set:
        """Un comando que dispara un evento de otro contexto o un mensaje de un SA. aporta: los datos que le llegan por
        su nombre; llegan: todos los que trae (para las correspondencias y las condiciones). con fija valores de su
        entrada, correspondencias {dato de la entrada: dato que llega} toma un dato que llega con otro nombre (D2),
        si o salvo lo dispara solo si se cumple la condición, y si_existe: true solo si su raíz existe (si no existe,
        el evento no le aplica: no es un error). Devuelve los datos que llegan y el comando usa."""
        op = self.mapa(op, d, list(OPCIONES_DISPARO))
        ent = entradas_cmd[cmd]["entrada"]
        aporta = dict(aporta)
        usados = {k for k in aporta if k in ent}
        for k, v in self.mapa(op.get("con"), f"{d} > con").items():
            if k not in ent:
                self.error(f"{d} > con", f'"{k}" no está en la entrada de "{cmd}"')
            elif not valor_valido(v, ent[k]):
                self.error(f"{d} > con", f'el valor {v!r} no es válido para "{k}" ({ent[k]["tipo"]})')
            else:
                aporta[k] = ent[k]
        for k, dato in self.mapa(op.get("correspondencias"), f"{d} > correspondencias").items():
            if k not in ent:
                self.error(f"{d} > correspondencias", f'"{k}" no está en la entrada de "{cmd}"')
            elif not isinstance(dato, str) or dato not in llegan:
                self.error(f"{d} > correspondencias", f'"{k}" se toma de "{dato}", que no llega con {quien}')
            elif not mismo_tipo(llegan[dato], ent[k]):
                self.error(f"{d} > correspondencias", f'"{dato}" llega como {llegan[dato]["tipo"]} y "{cmd}" espera "{k}" como {ent[k]["tipo"]}')
            else:
                aporta[k] = llegan[dato]
                usados.add(dato)
        self.si_salvo(op, llegan, d, frozenset(llegan))
        if "si_existe" in op:
            if op["si_existe"] not in (True, False):
                self.error(f"{d} > si_existe", "es true o false")
            elif op["si_existe"] and entradas_cmd[cmd]["crea"]:
                self.error(f"{d} > si_existe", f'"{cmd}" crea la raíz: no hay una raíz que pueda faltar')
        for k in ("si", "salvo"):
            usados |= set(op.get(k) or {}) if isinstance(op.get(k), dict) else set()
        for k, tk in aporta.items():
            if k in ent and not mismo_tipo(ent[k], tk):
                self.error(d, f'"{k}" llega como {tk["tipo"]} y "{cmd}" lo espera como {ent[k]["tipo"]}')
        for k, tk in ent.items():
            if not tk["opcional"] and k not in aporta:
                self.error(d, f'"{cmd}" necesita "{k}" y {quien} no lo trae (ni con ni correspondencias)')
        return usados

    # ------------------------------------------------------------ raíces (una por agregado, G2)
    def preparar_raiz(self, nombre_raiz: str, ag: dict, r_yaml) -> dict:
        """Identidad, estado y datos de una raíz. No cambia la raíz actual (ver usar)."""
        r = self.mapa(r_yaml, f"raices > {nombre_raiz}", ["identidad", "estado", "entidades"], ["identidad", "estado"])
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
                if t_parte["lista"] or t_parte["opcional"] or t_parte["base"] not in ("string", "int", "enum", "DateOnly", "DateTime"):
                    self.error(dp, f'una parte de la identidad es string, int, enum, DateOnly o DateTime, obligatoria; aquí es {t_parte["tipo"]}')
                id_de.append(parte)
        # Entidades (G9): cada una dice cuál de sus campos es su identidad dentro de la raíz.
        ents_m = {e["nombre"]: e for e in ag["entidades"]}
        ents_y = self.mapa(r.get("entidades"), f"raices > {nombre_raiz} > entidades")
        self.cubre(f"raices > {nombre_raiz} > entidades", ents_y, ents_m, "entidad de la raíz")
        entidades = {}
        for n_e in sorted(set(ents_y) & set(ents_m)):
            de_e = f"raices > {nombre_raiz} > entidades > {n_e}"
            x_e = self.mapa(ents_y[n_e], de_e, ["identidad"], ["identidad"])
            campos_e = {c["nombre"]: c for c in ents_m[n_e]["campos"]}
            ide = x_e.get("identidad")
            if ide not in campos_e:
                self.error(f"{de_e} > identidad", f'"{ide}" no es un campo de la entidad; campos: {", ".join(campos_e)}')
                continue
            t_e = tipos.interpretar(campos_e[ide]["tipo"])
            if t_e["lista"] or t_e["opcional"] or t_e["base"] not in ("string", "int"):
                self.error(f"{de_e} > identidad", f'la identidad de una entidad es un campo string o int obligatorio; "{ide}" es {t_e["tipo"]}')
            if ents_m[n_e]["compuesto_por"] != ag["raiz"]["id"]:
                self.error(de_e, "solo se generan entidades que compone la raíz")
            entidades[n_e] = ide
        for v in ag["objetos_valor"]:
            if v["compuesto_por"] != ag["raiz"]["id"]:
                self.error(f"raices > {nombre_raiz}", f'"{v["nombre"]}" lo compone una entidad: todavía no se genera (G9)')
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
                "consecutivo": consecutivo, "recibida": recibida, "entidades": entidades,
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
                                          "eventos_de_otros_contextos", "servicios_sa", "politicas", "escenarios"],
                      ["contexto", "raices", "comandos", "eventos", "consultas", "servicios_sa"])
        ctxs = {c["nombre"]: c for c in self.m["contextos"]}
        if s.get("contexto") not in ctxs:
            self.error("contexto", f'"{s.get("contexto")}" no está en el JSON; contextos: {", ".join(ctxs)}')
            return
        ctx = ctxs[s["contexto"]]
        for e in ctx["enums"]:
            self.enums[e["nombre"]] = e["valores"]
        # Los objetos de valor y las entidades del contexto se pueden usar como List<...> en el YAML (G4, G9).
        tipos.usar_objetos({v["nombre"]: {c["nombre"]: c for c in v["campos"]}
                            for a in ctx["agregados"] for v in a["objetos_valor"] + a["entidades"]})

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
        self.mensajes_crudos: dict[str, dict] = {}      # SA -> mensajes que recibe (G7), se revisan después de los comandos
        self.envios_crudos: dict[str, dict] = {}        # SA -> mensajes que envía (G11), se revisan con los eventos
        for n in sorted(set(sas_y) & set(sas_m)):
            d = f"servicios_sa > {n}"
            # Un SA que llama la aplicación (sale) declara entrada, salida y respuestas simuladas; uno que recibe lo que el
            # sistema externo le envía a la aplicación (G7) declara recibe. Puede tener las dos partes.
            x = self.mapa(sas_y[n], d, ["entrada", "salida", "respuesta_por_defecto", "casos", "recibe", "envia"],
                          [] if {"recibe", "envia"} & set(sas_y[n] or {}) else ["entrada", "salida", "respuesta_por_defecto"])
            sale = any(k in x for k in ("entrada", "salida", "respuesta_por_defecto"))
            if sale:
                for k in ("entrada", "salida", "respuesta_por_defecto"):
                    if k not in x:
                        self.error(d, f'falta la clave "{k}" (un SA que la aplicación llama declara entrada, salida y respuesta_por_defecto)')
            direcciones = {f["direccion"] for f in sas_m[n]["flujos"]}
            if "recibe" in x and "entra" not in direcciones:
                self.error(f"{d} > recibe", "en el modelo ningún flujo entra por la interfaz de este SA: no recibe nada")
            if "recibe" in x:
                self.mensajes_crudos[n] = self.mapa(x["recibe"], f"{d} > recibe")
            # G11: un SA al que la aplicación llama y espera respuesta necesita un flujo que entre; uno que solo sale
            # (lenguaje publicado) se declara con envia: sus mensajes salen con un evento del contexto.
            if sale and "entra" not in direcciones:
                self.error(d, "en el modelo ningún flujo entra por la interfaz de este SA: no responde. "
                              "Si la aplicación solo le envía datos, decláralo con envia")
            if "envia" in x:
                if "sale" not in direcciones:
                    self.error(f"{d} > envia", "en el modelo ningún flujo sale por la interfaz de este SA: no envía nada")
                self.envios_crudos[n] = self.mapa(x["envia"], f"{d} > envia")
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

            if sale:
                respuesta(x.get("respuesta_por_defecto"), f"{d} > respuesta_por_defecto")
            for i, caso in enumerate(self.lista(x.get("casos"), f"{d} > casos"), 1):
                caso = self.mapa(caso, f"{d} > casos {i}", ["si", "respuesta"], ["si", "respuesta"])
                self.condicion(caso.get("si"), ent, f"{d} > casos {i} > si")
                respuesta(caso.get("respuesta"), f"{d} > casos {i} > respuesta")
            sas[n] = {"entrada": ent, "salida": sal, "usado_por": ["envia"] if "envia" in x else [], "llamable": sale}

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
            c = self.mapa(cmds_y[n], d, ["crea", "desde", "a", "entrada", "valores", "requiere", "usa", "calculados", "guarda",
                                         "eventos", "resultados", "sobre", "temporizador"], ["entrada"])
            todas = c.get("sobre") == "todas"             # G8: revisa todas las raíces y publica un evento por cada elegida
            if "sobre" in c and not todas:
                self.error(f"{d} > sobre", 'en un comando solo se permite "sobre: todas"')
            if todas:
                for k in ("crea", "desde", "a", "valores", "requiere", "usa", "guarda", "resultados"):
                    if k in c:
                        self.error(d, f"un comando sobre todas las raíces no lleva {k}: solo elige raíces y publica sus eventos")
                if m["acceso"] in ESCRIBEN:
                    self.error(d, f"un comando sobre todas las raíces no escribe, y en el modelo su acceso es de {m['acceso']}")
            elif "temporizador" in c:
                self.error(f"{d} > temporizador", "el temporizador va en un comando sobre: todas")
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
            entradas_cmd[n] = {"entrada": ent, "crea": crea, "raiz": nombre_raiz, "todas": todas}
            if todas and "temporizador" in c:
                self.revisar_temporizador(c["temporizador"], ent, f"{d} > temporizador")
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
                # Si el evento solo se recuerda, sus correspondencias {dato del comando: dato del evento} le dan al
                # comando un dato que llega con otro nombre (D2). Se revisan en eventos_de_otros_contextos.
                corr_ev = x.get("correspondencias") if "dispara" not in x and isinstance(x.get("correspondencias"), dict) else {}
                for local, del_ev in corr_ev.items():
                    if isinstance(del_ev, str) and del_ev in datos_ev:
                        datos_ev[local] = datos_ev[del_ev]
                self.agregar(bolsa, datos_ev, f"{d} > requiere > {ev}")
                propios |= set(datos_ev)
                for k in datos_ev:
                    origenes_cmd.setdefault(k, []).append(f'evento "{ev}"')

            # Otras raíces que el comando lee en el modelo (G6): se cargan por el dato con el nombre de su identidad.
            if not todas:
                for lt in m["lee_tambien"]:
                    otra = self.raiz_por_id.get(lt["raiz_id"])
                    if otra and otra["id_nombre"] not in bolsa:
                        self.error(d, f'lee también "{otra["nombre"]}" y para cargarla hace falta "{otra["id_nombre"]}", que el comando no tiene')

            # Datos calculados del comando: salen de una regla y se escriben a mano. Cada uno dice de qué datos sale
            # (de: datos por su nombre o una raíz que el comando tiene) y se calcula en cuanto están: antes de llamar a
            # los SA o después del SA que da el último. Quedan disponibles por su nombre para lo que sigue.
            raices_cmd = set()
            if not crea and not todas:
                raices_cmd.add(nombre_raiz)
            if not todas:
                raices_cmd |= {self.raiz_por_id[lt["raiz_id"]]["nombre"] for lt in m["lee_tambien"] if lt["raiz_id"] in self.raiz_por_id}
            calc_de, calc_t = {}, {}
            for k, x_c in self.mapa(c.get("calculados"), f"{d} > calculados").items():
                dc = f"{d} > calculados > {k}"
                x_c = self.mapa(x_c, dc, ["tipo", "de"], ["tipo", "de"])
                if k in (self.id_nombre, "estado"):
                    self.error(dc, "la identidad y el estado no se calculan")
                    continue
                t_c = self.tipo(x_c.get("tipo"), f"{dc} > tipo")
                if t_c:
                    calc_t[k] = t_c
                calc_de[k] = [x for x in self.lista(x_c.get("de"), f"{dc} > de") if isinstance(x, str)]
                if not calc_de[k]:
                    self.error(f"{dc} > de", "di de qué datos sale el calculado (o de qué raíz)")
            usos = [uso_sa(i) for i in self.lista(c.get("usa"), f"{d} > usa")]
            salidas_llamada = []
            for nombre_sa, op in usos:
                sal_map = op.get("salida") if isinstance(op.get("salida"), dict) else {}
                salidas_llamada.append({sal_map.get(k, k) for k in sas[nombre_sa]["salida"]} if nombre_sa in sas else set())
            puntos = ubicar_calculados(calc_de, set(bolsa) | raices_cmd, salidas_llamada)

            def calcular(lista_c):
                falla = False
                for k in lista_c:
                    if k is None:                         # los que siguen no tienen sus datos en ningún momento
                        falla = True
                        continue
                    if falla:
                        faltan = [x for x in calc_de[k] if x not in bolsa and x not in raices_cmd]
                        self.error(f"{d} > calculados > {k}", "sale de " + ", ".join(f'"{x}"' for x in faltan)
                                   + ", que el comando no tiene (ni antes ni después de sus SA)")
                    elif k in calc_t:
                        self.agregar(bolsa, {k: calc_t[k]}, f"{d} > calculados > {k}")
                        propios.add(k)
                        origenes_cmd.setdefault(k, []).append("calculado")

            # Servicios SA que usa, en orden: piden datos de la bolsa y le agregan su salida. Cada llamada puede fijar
            # datos de la entrada del SA (con), tomarlos de un dato con otro nombre (entrada), renombrar su salida
            # (salida) y hacerse solo si se cumple una condición (si, salvo): entonces su salida es opcional.
            calcular(puntos[0])
            for i, (sa, op) in enumerate(usos, 1):
                du = f"{d} > usa > {sa}"
                if sa not in sas:
                    self.error(f"{d} > usa", f'"{sa}" no es un servicio SA del contexto')
                    calcular(puntos[i])
                    continue
                if not sas[sa]["llamable"]:
                    self.error(du, "este SA no responde (solo recibe o envía): no se llama con usa")
                    calcular(puntos[i])
                    continue
                op = self.mapa(op, du, list(OPCIONES_USO_SA))
                sas[sa]["usado_por"].append(n)
                ent_sa = sas[sa]["entrada"]
                fijos = self.mapa(op.get("con"), f"{du} > con")
                for k, val in fijos.items():
                    if k not in ent_sa:
                        self.error(f"{du} > con", f'"{k}" no está en la entrada del SA')
                    elif not valor_valido(val, ent_sa[k]):
                        self.error(f"{du} > con", f'el valor {val!r} no es válido para "{k}" ({ent_sa[k]["tipo"]})')
                corr = self.mapa(op.get("entrada"), f"{du} > entrada")
                for k, dato in corr.items():
                    if k not in ent_sa:
                        self.error(f"{du} > entrada", f'"{k}" no está en la entrada del SA')
                    elif k in fijos:
                        self.error(f"{du} > entrada", f'"{k}" ya tiene un valor fijo en con')
                    elif not isinstance(dato, str):
                        self.error(f"{du} > entrada", f'"{k}" se toma de un dato: escribe su nombre')
                    else:
                        self.pide(bolsa, {dato: ent_sa[k]}, du, f'el servicio SA "{sa}" ("{k}")', propios)
                # Lo demás va por su nombre; un dato opcional del SA que el comando no tiene va en null.
                self.pide(bolsa, {k: tk for k, tk in ent_sa.items() if k not in fijos and k not in corr
                                  and not (tk["opcional"] and k not in bolsa)}, du, f'el servicio SA "{sa}"', propios)
                self.si_salvo(op, bolsa, du, propios)
                condicional = "si" in op or "salvo" in op
                sal_map = self.mapa(op.get("salida"), f"{du} > salida")
                for k, nuevo in sal_map.items():
                    if k not in sas[sa]["salida"]:
                        self.error(f"{du} > salida", f'"{k}" no está en la salida del SA')
                    elif not isinstance(nuevo, str) or not nuevo.strip():
                        self.error(f"{du} > salida", f'"{k}" se renombra con un nombre de dato')
                salida = {}
                for k, tk in sas[sa]["salida"].items():
                    nuevo = sal_map.get(k, k)
                    if isinstance(nuevo, str):
                        salida[nuevo] = opcional(tk) if condicional else tk
                self.agregar(bolsa, salida, du)
                propios |= set(salida)
                for k in salida:
                    origenes_cmd.setdefault(k, []).append(f'SA "{sa}"')
                calcular(puntos[i])
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
                    if not campo["opcional"] and not campo["lista"] and campo["nombre"] not in guardados:
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
                if not crea and not todas and desde is None:
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
        # ---- mensajes que reciben los SA (G7): disparan un comando, como un evento de otro contexto, y pueden crear la raíz.
        self.mensajes_sa = {}
        for sa, mensajes in sorted(self.mensajes_crudos.items()):
            for msj, x in sorted(mensajes.items()):
                d = f"servicios_sa > {sa} > recibe > {msj}"
                x = self.mapa(x, d, ["dispara", "con", "correspondencias", "datos"], ["dispara", "datos"])
                if not isinstance(x.get("dispara"), str):
                    for k in ("con", "correspondencias"):
                        if k in x:
                            self.error(f"{d} > {k}", f"con varios comandos, {k} va en cada comando de dispara")
                if msj in entradas_cmd or msj in (s.get("consultas") or {}) or msj in (s.get("eventos_de_otros_contextos") or {}):
                    self.error(d, f'"{msj}" ya es el nombre de un comando, una consulta o un evento: los nombres no se repiten')
                # Puede disparar varios comandos (en orden; si uno falla, los siguientes no corren). Todos sus comandos
                # trabajan con raíces de la misma identidad.
                lista = disparos(x)
                if not lista:
                    self.error(f"{d} > dispara", "es un comando, una lista de comandos o {comando: {con, correspondencias, si, salvo}}")
                datos, usados, cmds = None, set(), []
                for cmd, op in lista:
                    if cmd not in entradas_cmd:
                        self.error(d, f'dispara "{cmd}", que no es un comando especificado del contexto')
                        continue
                    if entradas_cmd[cmd]["todas"]:
                        self.error(d, f'"{cmd}" es un comando sobre todas las raíces: un mensaje no lo dispara')
                        continue
                    rc = self.raices[entradas_cmd[cmd]["raiz"]]
                    if datos is None:
                        self.usar(rc)
                        datos = self.campos(x.get("datos"), f"{d} > datos", permitidos=(self.id_nombre,))
                    elif rc["id_nombre"] != self.id_nombre:
                        self.error(d, f'"{cmd}" trabaja con "{rc["id_nombre"]}" y el primer comando con "{self.id_nombre}": '
                                      "los comandos de un mensaje usan la misma identidad")
                        continue
                    no_crea = not entradas_cmd[cmd]["crea"]
                    if no_crea and self.id_nombre not in datos:
                        self.error(f"{d} > datos", f'dispara "{cmd}", que trabaja sobre una raíz existente: debe traer "{self.id_nombre}"')
                    aporta = {k: v for k, v in datos.items() if not (no_crea and k == self.id_nombre)}
                    usados |= self.revisar_disparo(cmd, op, aporta, datos, entradas_cmd, f"{d} > {cmd}", "el mensaje")
                    cmds.append(cmd)
                for k in sorted(set(datos or {}) - usados):
                    if k != self.id_nombre:
                        self.aviso(d, f'"{k}" no está en la entrada de ningún comando que dispara: no se usa')
                if sa in sas:
                    sas[sa]["usado_por"].append(f'recibe "{msj}"')
                if cmds:
                    self.mensajes_sa[msj] = {"sa": sa, "dispara": cmds[0], "comandos": cmds, "datos": datos or {}}
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
        # Sin entrada en la sección politicas, cada evento dispara el comando por su cuenta. Con entrada (G10, D7):
        # si/salvo (solo si se cumple), con y correspondencias; y para varios disparos, junto_con (deben llegar todos)
        # y uno_de (y además uno de estos, cada uno con su con).
        cmd_por_id = {c["id"]: c["nombre"] for c in ctx["comandos"]}
        evs_de: dict[str, list[str]] = {}
        for p in ctx["politicas"]:
            evs_de.setdefault(cmd_por_id.get(p["comando_id"]), []).append(ev_por_id.get(p["evento_id"]))
        pol_y = self.mapa(s.get("politicas"), "politicas")
        for cmd in sorted(set(pol_y) - set(evs_de)):
            self.error(f"politicas > {cmd}", "en el modelo ningún evento del contexto dispara este comando")

        def llegan_con(ev):                               # los datos de un evento del contexto, con su identidad
            ev_m = next((e for e in ctx["eventos"] if e["nombre"] == ev), None)
            r_ev = self.raiz_por_agregado.get(ev_m["agregado_id"]) if ev_m else None
            return {**datos_evento.get(ev, {}), **({r_ev["id_nombre"]: tipos.interpretar("string")} if r_ev else {})}, r_ev

        for cmd, evs in sorted(evs_de.items()):
            if cmd not in entradas_cmd or any(ev not in datos_evento for ev in evs):
                continue
            d = f"politicas > {cmd}"
            x = self.mapa(pol_y.get(cmd), d, ["junto_con", "uno_de", "si", "salvo", "con", "correspondencias"])
            r_cmd = self.raices.get(entradas_cmd[cmd]["raiz"])
            crea, ent = entradas_cmd[cmd]["crea"], entradas_cmd[cmd]["entrada"]
            for ev in evs:
                _, r_ev = llegan_con(ev)
                if r_ev and r_cmd and not crea and r_ev["id_nombre"] != r_cmd["id_nombre"]:
                    self.error(f'política "{ev}" dispara "{cmd}"', f'el evento lleva "{r_ev["id_nombre"]}" y "{cmd}" necesita '
                               f'"{r_cmd["id_nombre"]}": una política entre raíces con distinta identidad todavía no se genera')
            junto = [e for e in self.lista(x.get("junto_con"), f"{d} > junto_con") if isinstance(e, str)]
            uno_y = x.get("uno_de")
            uno = {k: (v or {}) for k, v in uno_y.items()} if isinstance(uno_y, dict) else \
                {k: {} for k in self.lista(uno_y, f"{d} > uno_de") if isinstance(k, str)}
            if not (junto or uno):                        # un disparo por evento, con las opciones de la entrada
                for ev in evs:
                    llegan, _ = llegan_con(ev)
                    self.revisar_disparo(cmd, x, llegan, llegan, entradas_cmd,
                                         d if cmd in pol_y else f'política "{ev}" dispara "{cmd}"', f'"{ev}"')
                continue
            # Varios disparos (D7): el comando corre cuando llegaron todos los de junto_con y uno de los de uno_de, para la
            # misma identidad. Sus datos salen de los eventos que llegaron, por su nombre.
            if sorted(set(junto) | set(uno)) != sorted(evs) or set(junto) & set(uno):
                self.error(d, f'junto_con y uno_de nombran, sin repetir, los eventos que disparan "{cmd}" en el modelo: '
                              + ", ".join(sorted(evs)))
                continue
            for k in ("si", "salvo"):
                if k in x:
                    self.error(f"{d} > {k}", "si y salvo van en una política de un solo disparo")
            con = self.mapa(x.get("con"), f"{d} > con")
            for k, v in con.items():
                if k not in ent:
                    self.error(f"{d} > con", f'"{k}" no está en la entrada de "{cmd}"')
                elif not valor_valido(v, ent[k]):
                    self.error(f"{d} > con", f'el valor {v!r} no es válido para "{k}" ({ent[k]["tipo"]})')
            corr = self.mapa(x.get("correspondencias"), f"{d} > correspondencias")
            seguros = {}
            for ev in junto:
                seguros.update(llegan_con(ev)[0])
            por_uno = {}
            for ev, o in uno.items():
                o = self.mapa(o, f"{d} > uno_de > {ev}", ["con"])
                llegan = dict(llegan_con(ev)[0])
                for k, v in self.mapa(o.get("con"), f"{d} > uno_de > {ev} > con").items():
                    if k not in ent:
                        self.error(f"{d} > uno_de > {ev} > con", f'"{k}" no está en la entrada de "{cmd}"')
                    elif not valor_valido(v, ent[k]):
                        self.error(f"{d} > uno_de > {ev} > con", f'el valor {v!r} no es válido para "{k}" ({ent[k]["tipo"]})')
                    else:
                        llegan[k] = ent[k]
                por_uno[ev] = llegan
            for k, tk in ent.items():
                fuente_k = corr.get(k, k)
                if k in con:
                    continue
                if k in corr and not isinstance(fuente_k, str):
                    self.error(f"{d} > correspondencias", f'"{k}" se toma de un dato: escribe su nombre')
                    continue
                if fuente_k in seguros:
                    t_llega = seguros[fuente_k]
                elif por_uno and all(fuente_k in ll or k in ll for ll in por_uno.values()):
                    t_llega = next(ll.get(fuente_k) or ll[k] for ll in por_uno.values())
                elif any(fuente_k in ll or k in ll for ll in por_uno.values()):
                    if not tk["opcional"]:
                        self.error(d, f'"{cmd}" necesita "{k}" y solo lo traen algunos de uno_de: debe ser opcional')
                    continue
                else:
                    if not tk["opcional"]:
                        self.error(d, f'"{cmd}" necesita "{k}" y ningún evento lo trae (ni con ni correspondencias)')
                    continue
                if not mismo_tipo(t_llega, tk):
                    self.error(d, f'"{fuente_k}" llega como {t_llega["tipo"]} y "{cmd}" espera "{k}" como {tk["tipo"]}')

        # ---- mensajes que envían los SA (G11): salen cuando ocurre un evento del contexto, con sus datos por nombre.
        self.envios_sa = {}
        for sa, envios in sorted(self.envios_crudos.items()):
            for msj, x in sorted(envios.items()):
                d = f"servicios_sa > {sa} > envia > {msj}"
                x = self.mapa(x, d, ["cuando", "datos"], ["cuando", "datos"])
                ev = x.get("cuando")
                if ev not in datos_evento:
                    self.error(f"{d} > cuando", f'"{ev}" no es un evento especificado del contexto')
                    continue
                if msj in self.mensajes_sa or msj in entradas_cmd or msj in (s.get("consultas") or {}):
                    self.error(d, f'"{msj}" ya es el nombre de un mensaje, un comando o una consulta')
                llegan, _ = llegan_con(ev)
                datos = self.campos(x.get("datos"), f"{d} > datos", libres=True)
                for k, tk in datos.items():
                    if k not in llegan:
                        self.error(f"{d} > datos", f'"{k}" no lo trae "{ev}"')
                    elif not mismo_tipo(llegan[k], tk):
                        self.error(f"{d} > datos", f'"{k}" llega en "{ev}" como {llegan[k]["tipo"]} y aquí es {tk["tipo"]}')
                self.envios_sa[msj] = {"sa": sa, "cuando": ev, "datos": datos}

        # ---- consultas
        qs_m = {q["nombre"]: q for q in ctx["consultas"]}
        qs_y = self.mapa(s.get("consultas"), "consultas")
        self.cubre("consultas", qs_y, qs_m, "consulta")
        for n in sorted(set(qs_y) & set(qs_m)):
            d = f"consultas > {n}"
            q = self.mapa(qs_y[n], d, ["entrada", "sobre", "de", "filtro", "filtro_manual", "salida", "agrega", "lista",
                                       "orden", "calculados"], ["entrada"])
            if "salida" not in q and "calculados" not in q:
                self.error(d, "debe tener salida o calculados")
            # La raíz de la consulta: la única que lee, o la que dice "de" (sobre cuál recorre, si lee varias).
            leidas = [self.raiz_por_id[x["raiz_id"]]["nombre"] for x in qs_m[n]["lee"] if x["raiz_id"] in self.raiz_por_id]
            if "de" in q:
                if "sobre" not in q and len(leidas) < 2:
                    self.error(f"{d} > de", "de va con sobre: todas o en una consulta que lee varias raíces")
                if q["de"] not in leidas:
                    self.error(f"{d} > de", f'"{q["de"]}" no es una raíz que la consulta lea en el modelo; lee: {", ".join(leidas)}')
                    continue
                nombre_q = q["de"]
            elif len(leidas) == 1:
                nombre_q = leidas[0]
            else:
                self.error(d, f'lee {len(leidas)} raíces ({", ".join(leidas)}): di con "de" cuál recorre (sobre: todas) '
                              "o por la identidad de cuál consulta")
                continue
            con_raiz, todos, *_ = self.usar(self.raices[nombre_q])
            if "sobre" in q:
                self.revisar_consulta_sobre_todas(q, d, con_raiz)
                continue
            for k in ("filtro", "filtro_manual", "agrega", "lista", "orden"):
                if k in q:
                    self.error(d, f"{k} solo va con sobre: todas")
            bolsa = dict(con_raiz)
            # G5: las demás raíces que lee se cargan con la misma identidad; sus datos llegan opcionales (si esa raíz
            # no existe, vacíos), y uno que se llama como uno de la raíz de la consulta no se toma.
            for otra in dict.fromkeys(leidas):
                if otra == nombre_q:
                    continue
                ro = self.raices[otra]
                if ro["id_nombre"] != self.id_nombre:
                    self.error(d, f'lee "{otra}", que se identifica con "{ro["id_nombre"]}", y la consulta va por "{self.id_nombre}": '
                                  "las raíces de una consulta por identidad tienen la misma identidad")
                    continue
                for k, tk in ro["con_raiz"].items():
                    if k not in bolsa and k != "estado":
                        bolsa[k] = opcional(tk)
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
        self.identidad_externos: dict[str, str] = {}      # evento de otro contexto -> dato con que llega
        for n in sorted(ext):
            d = f"eventos_de_otros_contextos > {n}"
            x = self.mapa(ext[n], d, ["de", "identidad", "dispara", "con", "correspondencias", "junto_con", "datos"], ["de", "datos"])
            if n in evs_m:
                self.error(d, "es un evento de este contexto, no de otro")
            elif n not in catalogo:
                self.error(d, f'"{n}" no existe en el modelo como evento de otro contexto')
            elif x.get("de") not in catalogo[n]:
                self.error(d, f'en el modelo "{n}" es de {", ".join(catalogo[n])}, no de "{x.get("de")}"')
            # La raíz del evento: la del (primer) comando que dispara; si no dispara y hay varias raíces, su identidad
            # se escribe. dispara puede ser un comando o varios, cada uno con sus opciones (en orden; si uno falla, los
            # siguientes no corren).
            lista = disparos(x) if "dispara" in x else []
            if "dispara" in x and not lista:
                self.error(f"{d} > dispara", "es un comando, una lista de comandos o {comando: {con, correspondencias, si, salvo}}")
            varios = "dispara" in x and not isinstance(x.get("dispara"), str)
            for k in ("con", "correspondencias", "junto_con"):
                if varios and k in x:
                    self.error(f"{d} > {k}", f"con varios comandos en dispara, {k} va en cada comando (junto_con, solo con uno)")
            cmd_d = lista[0][0] if lista else None
            if cmd_d in entradas_cmd:
                self.usar(self.raices[entradas_cmd[cmd_d]["raiz"]])
            elif "identidad" not in x and len(self.raices) > 1:
                self.error(f"{d} > identidad", "el contexto tiene varias raíces: di con qué dato llega el evento (identidad)")
            # identidad: el dato con que llega el evento (por defecto, la identidad de la raíz de este contexto).
            id_ev = x.get("identidad", self.id_nombre)
            self.identidad_externos[n] = id_ev            # para los contratos entre contextos (revisar_contratos)
            if not isinstance(id_ev, str) or not id_ev.strip():
                self.error(f"{d} > identidad", "es el nombre del dato con que llega el evento")
            elif id_ev in (x.get("datos") or {}):
                self.error(f"{d} > datos", f'"{id_ev}" es la identidad del evento: se agrega sola')
            if "dispara" not in x:
                # Sin dispara, el evento solo se recuerda, para los comandos que lo requieren (requiere). Puede llevar
                # correspondencias {dato del comando: dato del evento}, para un dato que llega con otro nombre (D2).
                for k in ("con", "junto_con"):
                    if k in x:
                        self.error(d, f"{k} solo va con dispara")
                if n not in self.requeridos:
                    self.error(d, "no dispara ningún comando y ningún comando lo requiere (requiere): nadie lo usa")
                datos_ev = self.campos(x.get("datos"), f"{d} > datos")
                for local, del_ev in self.mapa(x.get("correspondencias"), f"{d} > correspondencias").items():
                    if not isinstance(del_ev, str) or del_ev not in datos_ev:
                        self.error(f"{d} > correspondencias", f'"{local}" se toma de "{del_ev}", que no está en los datos del evento')
                    elif local in datos_ev:
                        self.error(f"{d} > correspondencias", f'"{local}" ya es un dato del evento: no necesita correspondencia')
                continue
            # La identidad de la raíz de cada comando: la del evento o (G3) un dato del evento con su nombre.
            ids_raiz = {self.raices[entradas_cmd[c_]["raiz"]]["id_nombre"] for c_, _ in lista if c_ in entradas_cmd}
            datos_ev = self.campos(x.get("datos"), f"{d} > datos", permitidos=tuple(ids_raiz - {id_ev}))
            junto = {}                                    # datos de los eventos de junto_con
            for otro in self.lista(x.get("junto_con"), f"{d} > junto_con"):
                o = ext.get(otro) if isinstance(ext.get(otro), dict) else None
                if o is None:
                    self.error(f"{d} > junto_con", f'"{otro}" no está en esta sección')
                    continue
                if o.get("dispara") != cmd_d or n not in (o.get("junto_con") or []):
                    self.error(f"{d} > junto_con", f'"{otro}" debe disparar "{cmd_d}" y nombrar a "{n}" en su junto_con')
                for k, t in (o.get("datos") or {}).items():
                    try:
                        junto.setdefault(k, tipos.interpretar(t))
                    except tipos.TipoInvalido:
                        pass
            # Con junto_con, el comando corre con el último que llega: las correspondencias valen para todo el grupo.
            corr_grupo = {}
            for otro in self.lista(x.get("junto_con"), f"{d} > junto_con"):
                if isinstance(ext.get(otro), dict) and isinstance(ext[otro].get("correspondencias"), dict):
                    corr_grupo.update(ext[otro]["correspondencias"])
            if corr_grupo and lista:
                lista = [(lista[0][0], {**lista[0][1], "correspondencias": {**corr_grupo, **(lista[0][1].get("correspondencias") or {})}})]
            usados = set()
            for cmd, op in lista:
                dd = f"{d} > dispara > {cmd}" if varios else d
                if cmd not in entradas_cmd:
                    self.error(d, f'dispara "{cmd}", que no es un comando especificado del contexto')
                    continue
                if entradas_cmd[cmd]["crea"]:
                    self.error(dd, f'"{cmd}" crea la raíz: un evento de otro contexto no puede dispararlo')
                    continue
                self.usar(self.raices[entradas_cmd[cmd]["raiz"]])
                otra_identidad = id_ev != self.id_nombre  # G3: la identidad de la raíz sale de los datos, por su nombre
                if otra_identidad and self.id_nombre not in datos_ev:
                    self.error(f"{d} > datos", f'llega con "{id_ev}" y dispara "{cmd}": debe traer "{self.id_nombre}", la identidad de la raíz')
                aporta = dict(datos_ev)
                if otra_identidad:                        # la identidad del evento también le sirve al comando
                    aporta.pop(self.id_nombre, None)
                    aporta.setdefault(id_ev, tipos.interpretar("string"))
                for k, t in junto.items():
                    aporta.setdefault(k, t)
                llegan = {**aporta, **datos_ev}
                usados |= self.revisar_disparo(cmd, op, aporta, llegan, entradas_cmd, dd, "el evento (ni junto_con)")
            for k in sorted((set(datos_ev) | set(junto)) - usados - ids_raiz):
                self.aviso(d, f'"{k}" no está en la entrada de ningún comando que dispara: no se usa')

        # ---- escenarios: solo se revisa que estén bien escritos (no se simulan los datos)
        self.revisar_escenarios(s, ctx, entradas_cmd, crean, ext, qs_y, ev_por_id)
        # Para los escenarios entre contextos (S4), que usan los pasos de este contexto.
        self.ctx, self.entradas_cmd, self.qs_y, self.ext_y = ctx, entradas_cmd, qs_y, ext

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
                self.error(d, "sin agrega, la consulta devuelve una lista: di su nombre con lista (por ejemplo, lista: elementos disponibles)")
            self.pide(con_raiz, sal, f"{d} > salida", "un elemento de la lista")
            for dato in self.lista(q.get("orden"), f"{d} > orden"):      # de menor a mayor, en el orden escrito
                if dato not in con_raiz or con_raiz[dato]["lista"]:
                    self.error(f"{d} > orden", f'"{dato}" no es un dato de la raíz (que no sea una lista) por el que se pueda ordenar')
            return
        for k in ("lista", "orden"):
            if k in q:
                self.error(f"{d} > {k}", "con agrega la consulta devuelve agregaciones, no una lista")
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

        codigos = {"comando": {404, 409, 422}, "consulta": {404, 422}, "evento de otro contexto": {202, 404, 409, 422},
                   "mensaje de un servicio SA": {404, 409, 422}}
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
                    if (qs_y[nombre] or {}).get("sobre") != "todas":   # por identidad: la de su raíz puede ir en con
                        q_m = next((q for q in ctx["consultas"] if q["nombre"] == nombre), None)
                        r_q = self.raiz_por_id.get(q_m["lee"][0]["raiz_id"]) if q_m and q_m["lee"] else None
                        if r_q:
                            campos.setdefault(r_q["id_nombre"], tipos.interpretar("string"))
                elif nombre in self.mensajes_sa:
                    tipo = "mensaje de un servicio SA"
                    campos = dict(self.mensajes_sa[nombre]["datos"])
                elif nombre in ext:
                    tipo = "evento de otro contexto"
                    x = ext[nombre] or {}
                    campos = {k: tipos.interpretar(v) for k, v in (x.get("datos") or {}).items()}
                    # Su identidad puede ir en con (la toma de con si no es la de la raíz; si lo es, de con o del escenario).
                    campos.setdefault(x["identidad"] if isinstance(x.get("identidad"), str) else self.id_nombre,
                                      tipos.interpretar("string"))
                else:
                    self.error(dp, f'"{nombre}" no es un comando, una consulta, un evento de otro contexto ni un mensaje de un SA del YAML')
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
                        cmds = [nombre] if tipo == "comando" else self.mensajes_sa[nombre]["comandos"] \
                            if tipo == "mensaje de un servicio SA" else [c_ for c_, _ in disparos(ext[nombre] or {})]
                        cmd = ", ".join(cmds)
                        posibles = set().union(*(alcanzables(c_) for c_ in cmds))
                        if esp not in posibles:
                            self.error(f"{dp} > espera", f'"{esp}" no es un evento que publique "{cmd}" (directo o por una política); '
                                                         f'posibles: {", ".join(sorted(posibles))}')
                elif isinstance(esp, dict) and "código" in esp:
                    # Un rechazo con su motivo: el código y los campos de la respuesta de error (H-J5-01).
                    esp = self.mapa(esp, f"{dp} > espera", ["código"] + list(CAMPOS_DE_ERROR))
                    cod = esp.get("código")
                    if not isinstance(cod, int) or isinstance(cod, bool) or cod not in codigos[tipo]:
                        self.error(f"{dp} > espera", f"el código {cod!r} no se permite en un {tipo}; se permiten {sorted(codigos[tipo])}")
                    if len(esp) == 1:
                        self.aviso(f"{dp} > espera", "con solo el código, escribe espera: <código>")
                    for k, v in esp.items():
                        if k != "código" and not isinstance(v, str):
                            self.error(f"{dp} > espera > {k}", "es un texto")
                    if "estado actual" in esp:
                        self.estados_validos(esp["estado actual"], f"{dp} > espera > estado actual")
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
                            elif salida_q[k]["lista"] and isinstance(v, int) and not isinstance(v, bool):
                                pass                      # una lista se compara por cuántos elementos tiene
                            elif not valor_valido(v, salida_q[k]):
                                self.error(f"{dp} > espera", f'el valor {v!r} no es válido para "{k}" ({salida_q[k]["tipo"]})')
                else:
                    self.error(f"{dp} > espera", "espera es un evento, un código HTTP o {dato de la salida: valor, ...}")
        # Un comando que dispara un evento de otro contexto usado en los escenarios también se prueba.
        llamados |= {c_ for n in list(llamados) if n in ext and isinstance(ext[n], dict) for c_, _ in disparos(ext[n])}
        llamados |= {c_ for n in list(llamados) if n in self.mensajes_sa for c_ in self.mensajes_sa[n]["comandos"]}
        # Y los que disparan las políticas internas de los comandos que se prueban.
        politica_de = {}
        for p in ctx["politicas"]:
            politica_de.setdefault(cmd_por_id.get(p["comando_id"]), set()).add(ev_por_id.get(p["evento_id"]))
        cambia = True
        while cambia:
            alcanzados = set().union(*(alcanzables(c_) for c_ in llamados if c_ in entradas_cmd)) if llamados else set()
            nuevos = {c_ for c_, evs in politica_de.items() if evs & alcanzados} - llamados
            llamados |= nuevos
            cambia = bool(nuevos)
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


CLAVE_ENTRE_CONTEXTOS = "escenarios_entre_contextos"


def es_entre_contextos(spec) -> bool:
    """Un YAML de escenarios entre contextos (S4) no especifica un contexto: solo tiene escenarios_entre_contextos."""
    return isinstance(spec, dict) and CLAVE_ENTRE_CONTEXTOS in spec


class RevisorEntreContextos:
    """Revisa los escenarios de punta a punta entre contextos (S4) contra los YAML de los contextos que usan.

    Cada paso es un comando, una consulta o un mensaje de un SA del contexto que dice en (los eventos entre contextos
    llegan por el bus, no se envían a mano); con fija datos de su entrada, y espera es un evento o una lista de eventos
    (de cualquier contexto generado) y de mensajes que envía un SA, un código o datos de una consulta.
    """

    def __init__(self, modelo: dict, spec, nombre_archivo: str, revisores: dict[str, "Revisor"]):
        self.m, self.s, self.archivo, self.revisores = modelo, spec, nombre_archivo, revisores
        self.errores: list[str] = []
        self.avisos: list[str] = []

    def error(self, donde: str, texto: str):
        self.errores.append(f"[{donde}] {texto}")

    def revisar(self):
        s = self.s if isinstance(self.s, dict) else {}
        for k in s:
            if k != CLAVE_ENTRE_CONTEXTOS:
                self.error("archivo", f'clave desconocida "{k}"; un YAML entre contextos solo tiene {CLAVE_ENTRE_CONTEXTOS}')
        esc = s.get(CLAVE_ENTRE_CONTEXTOS)
        if not isinstance(esc, dict) or not esc:
            self.error(CLAVE_ENTRE_CONTEXTOS, "escribe al menos un escenario, con su lista de pasos")
            return
        eventos = {e["nombre"] for c in self.m["contextos"] if c["nombre"] in self.revisores for e in c["eventos"]}
        envios = {n for r in self.revisores.values() for n in getattr(r, "envios_sa", {})}
        codigos = {"comando": {404, 409, 422}, "consulta": {404, 422}, "mensaje de un servicio SA": {404, 409, 422}}
        for nombre_e, pasos in esc.items():
            d = f"{CLAVE_ENTRE_CONTEXTOS} > {nombre_e}"
            if not isinstance(pasos, list) or not pasos:
                self.error(d, "el escenario es una lista de pasos")
                continue
            for i, paso in enumerate(pasos, 1):
                dp = f"{d} > paso {i}"
                if not isinstance(paso, dict) or len(paso) != 1:
                    self.error(dp, 'un paso es "nombre:" con en, con y espera')
                    continue
                nombre, op = next(iter(paso.items()))
                dp = f"{dp} ({nombre})"
                if not isinstance(op, dict):
                    self.error(dp, "falta en: el contexto del paso")
                    continue
                for k in op:
                    if k not in ("en", "con", "espera"):
                        self.error(dp, f'clave desconocida "{k}"; se permiten: en, con, espera')
                rv = self.revisores.get(op.get("en"))
                if rv is None:
                    self.error(f"{dp} > en", f'"{op.get("en")}" no es un contexto con YAML; están: {", ".join(sorted(self.revisores))}')
                    continue
                if nombre in rv.entradas_cmd:
                    tipo, campos = "comando", dict(rv.entradas_cmd[nombre]["entrada"])
                    if not rv.entradas_cmd[nombre]["crea"]:
                        campos.setdefault(rv.raices[rv.entradas_cmd[nombre]["raiz"]]["id_nombre"], tipos.interpretar("string"))
                elif nombre in rv.qs_y:
                    tipo = "consulta"
                    campos = {k: tipos.interpretar(v) for k, v in ((rv.qs_y[nombre] or {}).get("entrada") or {}).items()}
                    if (rv.qs_y[nombre] or {}).get("sobre") != "todas":
                        q_m = next((q for q in rv.ctx["consultas"] if q["nombre"] == nombre), None)
                        raiz_q = (rv.qs_y[nombre] or {}).get("de") or (rv.raiz_por_id[q_m["lee"][0]["raiz_id"]]["nombre"] if q_m else None)
                        if raiz_q in rv.raices:
                            campos.setdefault(rv.raices[raiz_q]["id_nombre"], tipos.interpretar("string"))
                elif nombre in rv.mensajes_sa:
                    tipo, campos = "mensaje de un servicio SA", dict(rv.mensajes_sa[nombre]["datos"])
                elif nombre in rv.ext_y:
                    self.error(dp, f'"{nombre}" es un evento de otro contexto: entre contextos llega solo por el bus (G12)')
                    continue
                else:
                    self.error(dp, f'"{nombre}" no es un comando, una consulta ni un mensaje de un SA de "{op["en"]}"')
                    continue
                objetos_antes = tipos.OBJETOS.copy()        # cada paso usa los objetos de valor de su contexto
                ctx_rv = rv.ctx
                tipos.usar_objetos({v["nombre"]: {c["nombre"]: c for c in v["campos"]}
                                    for a in ctx_rv["agregados"] for v in a["objetos_valor"] + a["entidades"]})
                con = op.get("con") or {}
                if not isinstance(con, dict):
                    self.error(f"{dp} > con", "es un mapa {dato: valor}")
                    con = {}
                for k, v in con.items():
                    if k not in campos:
                        self.error(f"{dp} > con", f'"{k}" no está en la entrada (o en los datos) de "{nombre}"')
                    elif not valor_valido(v, campos[k]):
                        self.error(f"{dp} > con", f'el valor {v!r} no es válido para "{k}" ({campos[k]["tipo"]})')
                if "espera" in op:
                    self.revisar_espera(op["espera"], tipo, nombre, rv, dp, eventos, envios, codigos)
                tipos.usar_objetos(objetos_antes)

    def revisar_espera(self, esp, tipo, nombre, rv, dp, eventos, envios, codigos):
        de = f"{dp} > espera"
        if isinstance(esp, bool):
            self.error(de, "espera no puede ser true o false")
        elif isinstance(esp, int):
            if esp not in codigos[tipo]:
                self.error(de, f"el código {esp} no se permite en un {tipo}; se permiten {sorted(codigos[tipo])}")
        elif isinstance(esp, (str, list)):
            if tipo == "consulta":
                self.error(de, "una consulta no publica eventos; usa espera: {dato: valor} o un código")
            for x in [esp] if isinstance(esp, str) else esp:
                if x not in eventos and x not in envios:
                    self.error(de, f'"{x}" no es un evento de un contexto generado ni un mensaje que envíe un SA')
        elif isinstance(esp, dict) and "código" in esp:
            cod = esp.get("código")
            if not isinstance(cod, int) or isinstance(cod, bool) or cod not in codigos[tipo]:
                self.error(de, f"el código {cod!r} no se permite en un {tipo}; se permiten {sorted(codigos[tipo])}")
            for k, v in esp.items():
                if k != "código" and (k not in CAMPOS_DE_ERROR or not isinstance(v, str)):
                    self.error(f"{de} > {k}", f'se afirma un campo de la respuesta de error ({", ".join(CAMPOS_DE_ERROR)}) con un texto')
        elif isinstance(esp, dict):
            if tipo != "consulta":
                self.error(de, "espera: {dato: valor, ...} solo va en una consulta")
                return
            qy = rv.qs_y[nombre] or {}
            salida_q = {}
            for k, v in {**(qy.get("salida") or {}), **(qy.get("calculados") or {})}.items():
                try:
                    salida_q[k] = tipos.interpretar(v)
                except tipos.TipoInvalido:
                    pass
            if isinstance(qy.get("lista"), str):
                salida_q = {qy["lista"]: tipos.interpretar("int")}
            for k, v in esp.items():
                if k not in salida_q:
                    self.error(de, f'"{k}" no está en la salida de "{nombre}"')
                elif salida_q[k]["lista"] and isinstance(v, int) and not isinstance(v, bool):
                    pass
                elif not valor_valido(v, salida_q[k]):
                    self.error(de, f'el valor {v!r} no es válido para "{k}" ({salida_q[k]["tipo"]})')
        else:
            self.error(de, "espera es un evento, una lista de eventos, un código HTTP o {dato de la salida: valor, ...}")


def revisores_de_contextos(modelo: dict, rutas: list[str]) -> tuple[dict[str, Revisor], list[str]]:
    """Revisa los YAML de contextos de la lista y devuelve sus revisores por contexto, y los errores."""
    revisores, errores = {}, []
    for ruta in rutas:
        spec = cargar_yaml(ruta)
        if es_entre_contextos(spec):
            continue
        rv = Revisor(modelo, spec, ruta)
        rv.id_nombre = ""
        rv.revisar()
        if rv.errores:
            errores.append(f"{ruta} tiene errores: revísalo primero")
        elif isinstance(spec, dict):
            revisores[spec.get("contexto")] = rv
    return revisores, errores


def revisar_contratos(modelo: dict, revisores: dict[str, Revisor], solo: str | None = None) -> tuple[list[str], list[str]]:
    """Contratos entre contextos (D2): lo que quien recibe un evento de otro contexto declara en
    eventos_de_otros_contextos debe llegar en ese evento tal como lo publica el YAML del contexto que lo publica.

    Por cada evento: el dato con que llega (identidad) y cada dato de datos están entre los que publica (la identidad
    de su raíz, datos y calculados), con el mismo tipo; y un dato obligatorio para quien recibe no es opcional para
    quien publica (podría llegar en null). Quien publica puede mandar más datos de los que se reciben.
    Con solo, revisa únicamente los pares en que está ese contexto. Devuelve (errores, avisos).
    """
    errores, avisos = [], []
    ctxs = {c["nombre"]: c for c in modelo["contextos"]}

    def objetos(nombre_ctx: str) -> dict:
        return {v["nombre"]: {c["nombre"]: c for c in v["campos"]}
                for a in ctxs[nombre_ctx]["agregados"] for v in a["objetos_valor"]}

    def tipo_en(nombre_ctx: str, texto):
        tipos.usar_objetos(objetos(nombre_ctx))    # List<objeto de valor> se interpreta con los del contexto
        try:
            return tipos.interpretar(texto)
        except tipos.TipoInvalido:
            return None                            # el error ya lo dio el Revisor de ese contexto

    def mismo_entre(tr: dict, receptor: str, tp: dict, emisor: str) -> bool:
        """Mismo tipo entre dos contextos: una lista de objetos de valor se compara por sus campos, no por el nombre."""
        if tr["base"] == "objeto" and tp["base"] == "objeto":
            cr, cp = objetos(receptor)[tr["objeto"]], objetos(emisor)[tp["objeto"]]
            return tr["lista"] == tp["lista"] and set(cr) == set(cp) and all(mismo_tipo(cr[k], cp[k]) for k in cr)
        return mismo_tipo(tr, tp)

    for receptor, rv in sorted(revisores.items()):
        ext = rv.s.get("eventos_de_otros_contextos") if isinstance(rv.s.get("eventos_de_otros_contextos"), dict) else {}
        for n, x in sorted(ext.items()):
            if not isinstance(x, dict):
                continue
            emisor = x.get("de")
            if solo and solo not in (receptor, emisor):
                continue
            d = f"{receptor} > eventos_de_otros_contextos > {n}"
            pub = revisores.get(emisor)
            if pub is None:
                avisos.append(f'[{d}] "{emisor}" no tiene YAML (o tiene errores): no se revisa contra lo que publica')
                continue
            ev_y = (pub.s.get("eventos") or {}).get(n)
            ev_m = next((e for e in ctxs[emisor]["eventos"] if e["nombre"] == n), None)
            if not isinstance(ev_y, dict) or ev_m is None or ev_m["agregado_id"] not in pub.raiz_por_agregado:
                continue                                  # lo dice el Revisor de quien publica
            id_pub = pub.raiz_por_agregado[ev_m["agregado_id"]]["id_nombre"]
            publica = {id_pub: tipos.interpretar("string")}
            for k, t in {**(ev_y.get("datos") or {}), **(ev_y.get("calculados") or {})}.items():
                tp = tipo_en(emisor, t)
                if tp:
                    publica[k] = tp
            lista_pub = ", ".join(f'"{k}"' for k in sorted(publica))
            id_rec = rv.identidad_externos.get(n)
            if isinstance(id_rec, str) and id_rec not in publica:
                errores.append(f'[{d} > identidad] llega con "{id_rec}", y "{emisor}" no lo publica en "{n}"; '
                               f"publica: {lista_pub}")
            for k, t in (x.get("datos") or {}).items():
                tr = tipo_en(receptor, t)
                if tr is None:
                    continue
                if k not in publica:
                    errores.append(f'[{d} > datos] "{k}" no llega: "{emisor}" no lo publica en "{n}"; publica: {lista_pub}')
                elif not mismo_entre(tr, receptor, publica[k], emisor):
                    errores.append(f'[{d} > datos] "{k}" se recibe como {tr["tipo"]} y "{emisor}" lo publica como '
                                   f'{publica[k]["tipo"]}')
                elif publica[k]["opcional"] and not tr["opcional"]:
                    errores.append(f'[{d} > datos] "{k}" es obligatorio aquí y "{emisor}" lo publica como opcional '
                                   f'({publica[k]["tipo"]}): puede llegar en null. Recíbelo como {tr["tipo"]}?')
    tipos.usar_objetos({})
    return errores, avisos


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
    if es_entre_contextos(spec):
        # Escenarios entre contextos: se revisan contra los YAML de contextos de la misma carpeta.
        rutas = sorted(str(p) for p in Path(ruta_yaml).parent.glob("*.yaml") if p.resolve() != Path(ruta_yaml).resolve())
        revisores, errores = revisores_de_contextos(modelo, rutas)
        rev = RevisorEntreContextos(modelo, spec, ruta_yaml, revisores)
        rev.revisar()
        errores += rev.errores
        err_c, av_c = revisar_contratos(modelo, revisores)
        errores += err_c
        for a in av_c:
            print("AVISO", a)
        if errores:
            print(f"\n{len(errores)} error(es) en {ruta_yaml}:", file=sys.stderr)
            for e in errores:
                print("  ERROR", e, file=sys.stderr)
            sys.exit(1)
        n = sum(len(p) for p in spec[CLAVE_ENTRE_CONTEXTOS].values())
        print(f"Escenarios entre contextos: {len(spec[CLAVE_ENTRE_CONTEXTOS])} escenarios, {n} pasos, "
              f"{len(revisores)} contextos con YAML.")
        print(f"\nEl YAML cumple con el modelo y con los YAML de los contextos: {ruta_yaml}")
        return
    rev = Revisor(modelo, spec, ruta_yaml)
    rev.id_nombre = ""
    rev.revisar()
    if not rev.errores and isinstance(spec, dict):
        # Contratos entre contextos (D2): contra los YAML de los demás contextos de la misma carpeta. Los que tienen
        # errores no se usan (cada uno los dice cuando se revisa).
        rutas = sorted(str(p) for p in Path(ruta_yaml).parent.glob("*.yaml") if p.resolve() != Path(ruta_yaml).resolve())
        otros, _ = revisores_de_contextos(modelo, rutas)
        otros[spec["contexto"]] = rev
        err_c, av_c = revisar_contratos(modelo, otros, solo=spec["contexto"])
        rev.errores += err_c
        rev.avisos += av_c
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
