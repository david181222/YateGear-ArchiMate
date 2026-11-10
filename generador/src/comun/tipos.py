"""Interpreta los tipos de los campos ("Campo: <nombre>" = tipo).

Tipos permitidos (V6-DEC-17):
  string, int, decimal, bool, DateOnly, DateTime
  List<tipo>            lista de uno de los anteriores
  sufijo ?              campo opcional, por ejemplo string? o List<string>?
  enum <Nombre>(a, b)   lista cerrada de valores; nombre y valores pueden tener espacios

Cada tipo básico tiene una entrada en TIPOS_BASICOS, con cómo se valida un valor, cómo se escribe en C#, su valor
de ejemplo y su valor provisional. Las listas, los opcionales, los enum y los objetos de valor envuelven a otro tipo:
los resuelve cada función antes de consultar la tabla.

El YAML de especificaciones usa estas mismas reglas, y además List<objeto de valor>: una lista de un objeto
de valor del contexto que se revisa (usar_objetos), por ejemplo List<Daño encontrado> en la entrada de un comando.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Callable


def cs_cadena(s: str) -> str:
    """El texto como literal de cadena de C#."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _es_fecha(v) -> bool:
    try:                                  # las fechas van como texto entre comillas
        return isinstance(v, str) and len(v) == 10 and bool(datetime.date.fromisoformat(v))
    except ValueError:
        return False


def _es_fecha_y_hora(v) -> bool:
    try:
        return isinstance(v, str) and "T" in v and bool(datetime.datetime.fromisoformat(v))
    except ValueError:
        return False


def _literal_fecha(v: str) -> str:
    d = datetime.date.fromisoformat(v)
    return f"new DateOnly({d.year}, {d.month}, {d.day})"


def _literal_fecha_y_hora(v: str) -> str:
    d = datetime.datetime.fromisoformat(v)
    return f"new DateTime({d.year}, {d.month}, {d.day}, {d.hour}, {d.minute}, {d.second})"


@dataclass(frozen=True)
class TipoBasico:
    """Todo lo que el generador necesita saber de un tipo básico. Para agregar un tipo se agrega una entrada a
    TIPOS_BASICOS: el revisor y el generador lo toman de ahí."""
    valido: Callable[[object], bool]          # ¿este valor del YAML es de este tipo?
    literal_cs: Callable[[object], str]       # el valor del YAML como literal de C#
    ejemplo: Callable[[str], object]          # valor de ejemplo para las pruebas, a partir del nombre del dato
    provisional: str                          # valor provisional de un dato calculado, en C#


TIPOS_BASICOS: dict[str, TipoBasico] = {
    "string": TipoBasico(valido=lambda v: isinstance(v, str), literal_cs=cs_cadena,
                         ejemplo=lambda nombre: nombre, provisional='""'),
    "int": TipoBasico(valido=lambda v: isinstance(v, int) and not isinstance(v, bool), literal_cs=str,
                      ejemplo=lambda nombre: 1, provisional="0"),
    "decimal": TipoBasico(valido=lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
                          literal_cs=lambda v: f"{v}m", ejemplo=lambda nombre: 100, provisional="0m"),
    "bool": TipoBasico(valido=lambda v: isinstance(v, bool), literal_cs=lambda v: "true" if v else "false",
                       ejemplo=lambda nombre: True, provisional="false"),
    "DateOnly": TipoBasico(valido=_es_fecha, literal_cs=_literal_fecha,
                           ejemplo=lambda nombre: "2026-02-01", provisional="default"),
    "DateTime": TipoBasico(valido=_es_fecha_y_hora, literal_cs=_literal_fecha_y_hora,
                           ejemplo=lambda nombre: "2026-02-01T09:00:00", provisional="default"),
}
BASICOS = tuple(TIPOS_BASICOS)
_ENUM = re.compile(r"^enum (?P<nombre>[^()?]+)\((?P<valores>[^()]+)\)$")
_LISTA = re.compile(r"^List<(?P<interno>[^<>]+)>$")


class TipoInvalido(ValueError):
    pass


# Objetos de valor del contexto que se revisa o se genera: nombre -> {campo: tipo}. Lo fija usar_objetos.
OBJETOS: dict[str, dict[str, dict]] = {}


def usar_objetos(objetos: dict[str, dict[str, dict]]):
    """Fija los objetos de valor que se pueden usar en List<objeto de valor> (los del contexto actual)."""
    OBJETOS.clear()
    OBJETOS.update(objetos)


def interpretar(texto: str) -> dict:
    """Devuelve el tipo ya separado en partes, o lanza TipoInvalido."""
    if not isinstance(texto, str) or texto != texto.strip() or not texto:
        raise TipoInvalido(f'tipo vacío o con espacios al inicio o al final: "{texto}"')
    t = texto
    opcional = t.endswith("?")
    if opcional:
        t = t[:-1]

    m = _ENUM.match(t)
    if m:
        nombre = m["nombre"].strip()
        valores = [v.strip() for v in m["valores"].split(",")]
        if not nombre or any(not v for v in valores):
            raise TipoInvalido(f'enum sin nombre o con un valor vacío: "{texto}"')
        if len(set(valores)) != len(valores):
            raise TipoInvalido(f'enum con valores repetidos: "{texto}"')
        return {"tipo": texto, "base": "enum", "lista": False, "opcional": opcional,
                "enum": {"nombre": nombre, "valores": valores}}

    m = _LISTA.match(t)
    if m:
        if m["interno"] in OBJETOS:
            return {"tipo": texto, "base": "objeto", "objeto": m["interno"], "lista": True, "opcional": opcional, "enum": None}
        if m["interno"] not in BASICOS:
            raise TipoInvalido(f'List<> solo admite {", ".join(BASICOS)} o un objeto de valor del contexto: "{texto}"')
        return {"tipo": texto, "base": m["interno"], "lista": True, "opcional": opcional, "enum": None}

    if t in BASICOS:
        return {"tipo": texto, "base": t, "lista": False, "opcional": opcional, "enum": None}

    raise TipoInvalido(f'tipo no permitido: "{texto}". Permitidos: {", ".join(BASICOS)}, '
                       'List<tipo>, sufijo ? y enum <Nombre>(valor, valor, ...)')
