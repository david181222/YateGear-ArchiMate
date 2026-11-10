"""Nombres de C# y rutas HTTP a partir de los nombres del modelo. Deterministas.

  pascal("precio por día")             -> "PrecioPorDia"
  pascal("referencia al CRM")          -> "ReferenciaAlCRM"   (las mayúsculas que ya hay se conservan)
  camel("número del arriendo")         -> "numeroDelArriendo"
  ruta("Confirmar la reserva")         -> "confirmar-la-reserva"
  variable("base")                     -> "@base"             (palabra reservada de C#)
  variable_local("datos")              -> "datos_"            (nombre que ya usa el código generado)

Se quitan las tildes y la diéresis, y la ñ queda como n. Cualquier otro signo separa palabras.
"""
from __future__ import annotations

import re
import unicodedata


# Palabras reservadas de C#: como identificador van con @ (el nombre sigue siendo el mismo para C# y para ASP.NET).
RESERVADAS_CS = frozenset("""
    abstract as base bool break byte case catch char checked class const continue decimal default delegate do double
    else enum event explicit extern false finally fixed float for foreach goto if implicit in int interface internal
    is lock long namespace new null object operator out override params private protected public readonly ref return
    sbyte sealed short sizeof stackalloc static string struct switch this throw true try typeof uint ulong unchecked
    unsafe ushort using virtual void volatile while""".split())
# Variables locales y parámetros que las plantillas ya usan en los manejadores, los receptores y las políticas.
LOCALES_DE_LAS_PLANTILLAS = frozenset("""
    bitacora bus comando consulta datos detener e elegidas elementos entrada espera evento eventos faltan json juntos
    manejador memoria mensaje raices receptor reloj repositorio respuesta respuestas resultado servicios""".split())


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


def variable(texto: str) -> str:
    """Nombre de un parámetro de C#: camelCase, con @ si es una palabra reservada ("base" -> "@base")."""
    n = camel(texto)
    return "@" + n if n in RESERVADAS_CS else n


def variable_local(texto: str) -> str:
    """Nombre de una variable local del código generado: como variable(), y con _ al final si las plantillas ya
    usan ese nombre (una raíz "Datos" -> "datos_")."""
    n = camel(texto)
    return n + "_" if n in LOCALES_DE_LAS_PLANTILLAS else variable(texto)
