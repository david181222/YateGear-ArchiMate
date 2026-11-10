"""Lee un modelo ArchiMate con pyArchimate y lo deja como un grafo simple.

Sirve para el XML de intercambio que exporta la ACLI y para el .archimate:
Model.read() de pyArchimate reconoce el formato solo.

El resto del generador no usa pyArchimate directamente: trabaja con el grafo
que devuelve leer(), donde cada concepto tiene su ID, su tipo, su nombre, su
documentación y sus propiedades, y cada relación su origen, su destino y,
si es de acceso, su tipo de acceso.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import logging
import xml.etree.ElementTree as ET

from pyArchimate.model import Model


# Cómo nombra cada lectura el tipo de acceso, llevado a una sola forma.
# .archimate: sin atributo = escritura, "1" = lectura, "2" = acceso, "3" = lectura y escritura.
# XML de intercambio y pyArchimate: Write, Read, Access, ReadWrite.
# En el XML, si falta el atributo, el esquema de The Open Group dice Write.
ACCESOS = {
    None: "escritura", "0": "escritura", "1": "lectura", "2": "acceso", "3": "lectura y escritura",
    "Write": "escritura", "Read": "lectura", "Access": "acceso", "ReadWrite": "lectura y escritura",
}


def tipo_corto(tipo: str) -> str:
    """'archimate:AccessRelationship' -> 'Access'; 'archimate:DataObject' -> 'DataObject'."""
    t = tipo.split(":")[-1]
    return t[: -len("Relationship")] if t.endswith("Relationship") else t


def tipo_normal(tipo: str, union: str | None = None) -> str:
    """Como tipo_corto, y además une la forma de escribir las uniones.

    .archimate: Junction con type="or" (sin atributo es "and"); XML de intercambio: OrJunction o AndJunction.
    """
    t = tipo_corto(tipo)
    if t == "Junction":
        return "OrJunction" if union == "or" else "AndJunction"
    return t


def acceso_normal(valor) -> str:
    return ACCESOS[None if valor is None else str(valor)]


def texto_normal(texto: str | None) -> str:
    """Quita lo que solo es forma de escribir: fin de línea CRLF, espacios al final de cada línea y al inicio o fin del texto."""
    if not texto:
        return ""
    lineas = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(linea.rstrip() for linea in lineas).strip()


def props_normales(props) -> list[tuple[str, str]]:
    return [(k, "" if v is None else str(v)) for k, v in props]


# ---------------------------------------------------------------- lectura cruda

class _Contador(logging.Handler):
    """Cuenta los avisos que escribe pyArchimate mientras lee."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.mensajes: list[str] = []

    def emit(self, record):
        self.mensajes.append(f"{record.levelname}: {record.getMessage()}")


def id_del_archivo(ruta: str) -> str:
    """ID del modelo tal como está en el archivo.

    pyArchimate le asigna al modelo un ID nuevo al azar en cada lectura, así que
    se toma del elemento raíz: "identifier" en el XML de intercambio, "id" en el .archimate.
    """
    for _, nodo in ET.iterparse(ruta, events=("start",)):
        return nodo.get("identifier") or nodo.get("id")


def _nodos(contenedor):
    hijos = contenedor.nodes() if callable(contenedor.nodes) else contenedor.nodes
    for n in hijos:
        yield n
        yield from _nodos(n)


def cargar_crudo(ruta: str) -> dict:
    """Lee el archivo con pyArchimate y devuelve sus valores tal como los entrega, sin normalizar."""
    contador = _Contador()
    raiz_log = logging.getLogger()
    raiz_log.addHandler(contador)
    try:
        modelo = Model()
        modelo.read(ruta)
    finally:
        raiz_log.removeHandler(contador)

    conceptos = {}
    for e in modelo.elements:
        conceptos[e.uuid] = {
            "clase": "elemento", "tipo": e.type, "nombre": e.name, "doc": e.desc,
            "props": list(e.props.items()), "origen": None, "destino": None, "acceso": None,
            "union": e.junction_type,
        }
    for r in modelo.relationships:
        conceptos[r.uuid] = {
            "clase": "relacion", "tipo": r.type, "nombre": r.name, "doc": r.desc,
            "props": list(r.props.items()),
            "origen": r.source.uuid if r.source is not None else None,
            "destino": r.target.uuid if r.target is not None else None,
            "acceso": None if r.access_type is None else str(r.access_type), "union": None,
        }
    vistas = {}
    for v in modelo.views:
        nodos = list(_nodos(v))
        vistas[v.uuid] = {
            "nombre": v.name,
            "nodos": len(nodos),
            "refs": sorted(n.ref for n in nodos if n.ref),
            "conexiones": sorted(c.ref for c in v.conns if c.ref),
        }
    return {"id": id_del_archivo(ruta), "nombre": modelo.name, "conceptos": conceptos,
            "vistas": vistas, "avisos": contador.mensajes}


# ---------------------------------------------------------------- grafo normalizado

@dataclass
class Concepto:
    id: str
    clase: str                     # "elemento" o "relacion"
    tipo: str                      # nombre corto ArchiMate: DataObject, Access, Composition...
    nombre: str
    documentacion: str
    propiedades: list[tuple[str, str]]
    origen: str | None = None      # solo relaciones
    destino: str | None = None
    acceso: str | None = None      # solo relaciones de acceso: lectura, escritura, acceso, lectura y escritura

    def prop(self, clave: str) -> str | None:
        return next((v for k, v in self.propiedades if k == clave), None)


@dataclass
class Grafo:
    id: str
    nombre: str
    conceptos: dict[str, Concepto]
    salen: dict[str, list[Concepto]] = field(default_factory=lambda: defaultdict(list))
    llegan: dict[str, list[Concepto]] = field(default_factory=lambda: defaultdict(list))
    avisos: list[str] = field(default_factory=list)

    def elementos(self, tipo: str | None = None) -> list[Concepto]:
        return sorted((c for c in self.conceptos.values()
                       if c.clase == "elemento" and (tipo is None or c.tipo == tipo)),
                      key=lambda c: (c.nombre, c.id))

    def relaciones(self) -> list[Concepto]:
        return sorted((c for c in self.conceptos.values() if c.clase == "relacion"), key=lambda c: c.id)


def normalizar(crudo: dict) -> Grafo:
    conceptos = {}
    for cid, c in crudo["conceptos"].items():
        conceptos[cid] = Concepto(
            id=cid, clase=c["clase"], tipo=tipo_normal(c["tipo"], c["union"]), nombre=c["nombre"] or "",
            documentacion=texto_normal(c["doc"]), propiedades=props_normales(c["props"]),
            origen=c["origen"], destino=c["destino"],
            acceso=acceso_normal(c["acceso"]) if tipo_corto(c["tipo"]) == "Access" else None,
        )
    g = Grafo(id=crudo["id"], nombre=crudo["nombre"] or "", conceptos=conceptos, avisos=crudo["avisos"])
    for r in g.relaciones():          # ordenadas por ID: las listas salen/llegan quedan en orden fijo
        g.salen[r.origen].append(r)
        g.llegan[r.destino].append(r)
    return g


def leer(ruta: str) -> Grafo:
    return normalizar(cargar_crudo(ruta))
