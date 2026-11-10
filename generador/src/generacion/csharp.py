"""Tipos, literales y expresiones de C# a partir de los tipos del modelo y del YAML."""
from __future__ import annotations

import textwrap

from comun import nombres, tipos
from comun.tipos import cs_cadena, TIPOS_BASICOS


class ErrorDeGeneracion(Exception):
    pass


# ------------------------------------------------------------ tipos y literales de C#

def cs_tipo(t: dict) -> str:
    base = nombres.pascal(t["enum"]["nombre"]) if t["base"] == "enum" else \
        nombres.pascal(t["objeto"]) if t["base"] == "objeto" else t["base"]
    texto = f"List<{base}>" if t["lista"] else base
    return texto + ("?" if t["opcional"] else "")


def cs_literal(v, t: dict) -> str:
    if v is None:
        return "null"
    if t["lista"]:
        uno = {**t, "lista": False, "opcional": False}
        return "[" + ", ".join(cs_literal(x, uno) for x in v) + "]"
    if t["base"] == "enum":
        return f'{nombres.pascal(t["enum"]["nombre"])}.{nombres.pascal(v)}'
    return TIPOS_BASICOS[t["base"]].literal_cs(v)


def provisional(t: dict) -> str:
    """Valor provisional de un dato calculado, sin advertencias del compilador."""
    if t["opcional"]:
        return "null"
    if t["lista"]:
        return "[]"
    basico = TIPOS_BASICOS.get(t["base"])
    return basico.provisional if basico else "default"        # un enum: su primer valor


def ejemplo(nombre: str, t: dict):
    """Valor de ejemplo, fijo, para pruebas.http."""
    if t["lista"]:
        return [ejemplo(nombre, {**t, "lista": False})]
    b = t["base"]
    if b == "enum":
        return nombres.pascal(t["enum"]["valores"][0])
    if b == "objeto":                       # un elemento de List<objeto de valor>: sus campos con valores de ejemplo
        return {nombres.camel(k): ejemplo(k, c) for k, c in tipos.OBJETOS[t["objeto"]].items()}
    return TIPOS_BASICOS[b].ejemplo(nombre)


def valor_json(v, t: dict):
    """Un valor del YAML tal como viaja en JSON (los enum, con su nombre de C#; los objetos de valor, en camelCase)."""
    if v is None or (t["lista"] and isinstance(v, int) and not isinstance(v, bool)):   # una lista, por su número
        return v
    if t["base"] == "objeto":
        campos = tipos.OBJETOS[t["objeto"]]
        return [{nombres.camel(k): valor_json(x, campos[k]) for k, x in e.items()} for e in v]
    if t["base"] == "enum":
        return [nombres.pascal(x) for x in v] if t["lista"] else nombres.pascal(v)
    return v


def xml(texto: str) -> str:
    return " ".join(texto.split("\n")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def descripcion_del_contrato(contrato: dict) -> str:
    """El contrato de un comando o una consulta como texto para la documentación de la API (OpenAPI)."""
    partes = [f'Entrada: {contrato["entrada"]}', f'Salida: {contrato["salida"]}']
    if contrato["reglas"]:
        partes.append(f'Reglas: {contrato["reglas"]}')
    return "\n\n".join(partes)


def lineas(texto: str, ancho: int = 100) -> list[str]:
    out = []
    for parrafo in texto.split("\n"):
        out += textwrap.wrap(parrafo, ancho) or [""]
    return out


class Ambito:
    """Datos disponibles por nombre (regla de los datos). La última capa agregada gana."""

    def __init__(self):
        self.capas: list[dict] = []

    def agregar(self, capa: dict):
        self.capas.append(capa)

    def con(self, capa: dict) -> "Ambito":
        """Una copia con una capa más, que gana sobre las anteriores."""
        a = Ambito()
        a.capas = self.capas + [capa]
        return a

    def buscar(self, nombre: str):
        for capa in reversed(self.capas):
            if nombre in capa:
                return capa[nombre]
        return None

    def expr(self, nombre: str, destino_opcional: bool) -> str:
        f = self.buscar(nombre)
        if f is None:
            raise ErrorDeGeneracion(f'el dato "{nombre}" no está disponible')
        e = f["opcional"] if destino_opcional else f["requerido"]
        if f["tipo"]["opcional"] and not destino_opcional:
            e = f'({e} ?? throw new DatoFaltante({cs_cadena(nombre)}))'
        return e


def fuente(expr: str, t: dict, expr_opcional: str | None = None) -> dict:
    return {"requerido": expr, "opcional": expr_opcional or expr, "tipo": t}
