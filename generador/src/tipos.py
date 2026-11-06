"""Interpreta los tipos de los campos ("Campo: <nombre>" = tipo).

Tipos permitidos (V6-DEC-17):
  string, int, decimal, bool, DateOnly, DateTime
  List<tipo>            lista de uno de los anteriores
  sufijo ?              campo opcional, por ejemplo string? o List<string>?
  enum <Nombre>(a, b)   lista cerrada de valores; nombre y valores pueden tener espacios

El YAML de especificaciones usa estas mismas reglas, y además List<objeto de valor>: una lista de un objeto
de valor del contexto que se revisa (usar_objetos), por ejemplo List<Daño encontrado> en la entrada de un comando.
"""
from __future__ import annotations

import re

BASICOS = ("string", "int", "decimal", "bool", "DateOnly", "DateTime")
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
