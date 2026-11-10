"""Tipos, valores y formas del YAML que usan el revisor y el generador."""
from __future__ import annotations

from comun import tipos

ESCRIBEN = ("escritura", "lectura y escritura")
# Campos de una respuesta de error que un escenario puede afirmar (espera: {código: ..., campo: valor}), y su nombre en JSON.
CAMPOS_DE_ERROR = {"regla": "regla", "requiere": "requiere", "identidad": "identidad", "operación": "operacion",
                   "estado actual": "estadoActual"}


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
    basico = tipos.TIPOS_BASICOS.get(b)
    return basico is not None and basico.valido(v)


# Comparaciones de una regla declarada (comandos > reglas): {dato: {comparación: valor}}, y su operador en C#.
COMPARACIONES = {"mayor_que": ">", "menor_que": "<", "minimo": ">=", "maximo": "<="}
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


CLAVE_ENTRE_CONTEXTOS = "escenarios_entre_contextos"


def es_entre_contextos(spec) -> bool:
    """Un YAML de escenarios entre contextos (S4) no especifica un contexto: solo tiene escenarios_entre_contextos."""
    return isinstance(spec, dict) and CLAVE_ENTRE_CONTEXTOS in spec
