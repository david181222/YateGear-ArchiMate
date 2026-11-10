"""Nombres de C# y rutas HTTP a partir de los nombres del modelo. Deterministas.

  pascal("precio por día")             -> "PrecioPorDia"
  pascal("referencia al CRM")          -> "ReferenciaAlCRM"   (las mayúsculas que ya hay se conservan)
  camel("número del arriendo")         -> "numeroDelArriendo"
  ruta("Confirmar la reserva")         -> "confirmar-la-reserva"

Se quitan las tildes y la diéresis, y la ñ queda como n. Cualquier otro signo separa palabras.
"""
from __future__ import annotations

import re
import unicodedata


class NombreInvalido(ValueError):
    pass


def sin_tildes(texto: str) -> str:
    # NFD separa la letra de su tilde (á -> a + ´, ñ -> n + ~); se borran las marcas.
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def palabras(texto: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", sin_tildes(texto))


def pascal(texto: str) -> str:
    p = palabras(texto)
    if not p:
        raise NombreInvalido(f'"{texto}" no tiene letras para formar un nombre de C#')
    nombre = "".join(w[0].upper() + w[1:] for w in p)
    if nombre[0].isdigit():
        raise NombreInvalido(f'"{texto}" empieza por un número: no sirve como nombre de C#')
    return nombre


def camel(texto: str) -> str:
    n = pascal(texto)
    return n[0].lower() + n[1:]


def ruta(texto: str) -> str:
    return "-".join(w.lower() for w in palabras(texto))
