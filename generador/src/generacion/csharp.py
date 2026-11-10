"""Tipos, literales y expresiones de C# a partir de los tipos del modelo y del YAML."""
from __future__ import annotations

import datetime
import textwrap

from comun import nombres, tipos


class ErrorDeGeneracion(Exception):
    pass


# ------------------------------------------------------------ tipos y literales de C#

def cs_tipo(t: dict) -> str:
    base = nombres.pascal(t["enum"]["nombre"]) if t["base"] == "enum" else \
        nombres.pascal(t["objeto"]) if t["base"] == "objeto" else t["base"]
    texto = f"List<{base}>" if t["lista"] else base
    return texto + ("?" if t["opcional"] else "")


def cs_cadena(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def cs_literal(v, t: dict) -> str:
    if v is None:
        return "null"
    if t["lista"]:
        uno = {**t, "lista": False, "opcional": False}
        return "[" + ", ".join(cs_literal(x, uno) for x in v) + "]"
    b = t["base"]
    if b == "enum":
        return f'{nombres.pascal(t["enum"]["nombre"])}.{nombres.pascal(v)}'
    if b == "string":
        return cs_cadena(v)
    if b == "int":
        return str(v)
    if b == "decimal":
        return f"{v}m"
    if b == "bool":
        return "true" if v else "false"
    if b == "DateOnly":
        d = datetime.date.fromisoformat(v)
        return f"new DateOnly({d.year}, {d.month}, {d.day})"
    d = datetime.datetime.fromisoformat(v)
    return f"new DateTime({d.year}, {d.month}, {d.day}, {d.hour}, {d.minute}, {d.second})"


def provisional(t: dict) -> str:
    """Valor provisional de un dato calculado, sin advertencias del compilador."""
    if t["opcional"]:
        return "null"
    if t["lista"]:
        return "[]"
    return {"string": '""', "int": "0", "decimal": "0m", "bool": "false"}.get(t["base"], "default")


def ejemplo(nombre: str, t: dict):
    """Valor de ejemplo, fijo, para pruebas.http."""
    if t["lista"]:
        return [ejemplo(nombre, {**t, "lista": False})]
    b = t["base"]
    if b == "enum":
        return nombres.pascal(t["enum"]["valores"][0])
    if b == "objeto":                       # un elemento de List<objeto de valor>: sus campos con valores de ejemplo
        return {nombres.camel(k): ejemplo(k, c) for k, c in tipos.OBJETOS[t["objeto"]].items()}
    return {"string": nombre, "int": 1, "decimal": 100, "bool": True,
            "DateOnly": "2026-02-01", "DateTime": "2026-02-01T09:00:00"}[b]


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
