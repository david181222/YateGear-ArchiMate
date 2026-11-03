"""Compara tres lecturas del modelo para decidir qué archivo lee el generador.

  A  el .archimate leído con el XML estándar de Python (referencia: lo que hay en el archivo)
  B  pyArchimate leyendo el .archimate
  C  pyArchimate leyendo el XML de intercambio que exporta la ACLI

Por cada aspecto cuenta las diferencias en crudo y después de normalizar lo que
solo es forma de escribir (ver leer.py). Termina con código 0 si C es igual a A
después de normalizar.

uso: python src/comparar_lectura.py <modelo.archimate> <modelo.xml>
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import Counter

import leer

XSI = "{http://www.w3.org/2001/XMLSchema-instance}type"
VISTAS = ("archimate:ArchimateDiagramModel", "archimate:SketchModel", "canvas:CanvasModel")


def crudo_referencia(ruta: str) -> dict:
    """Lectura A: el .archimate tal como está escrito, sin pyArchimate."""
    raiz = ET.parse(ruta).getroot()
    conceptos, vistas = {}, {}
    for e in raiz.iter("element"):
        tipo = e.get(XSI)
        if tipo in VISTAS:
            nodos = list(e.iter("child"))
            vistas[e.get("id")] = {
                "nombre": e.get("name"),
                "nodos": len(nodos),
                "refs": sorted(n.get("archimateElement") for n in nodos if n.get("archimateElement")),
                "conexiones": sorted(c.get("archimateRelationship") for c in e.iter("sourceConnection")
                                     if c.get("archimateRelationship")),
            }
            continue
        es_rel = tipo.endswith("Relationship")
        conceptos[e.get("id")] = {
            "clase": "relacion" if es_rel else "elemento", "tipo": tipo, "nombre": e.get("name"),
            "doc": e.findtext("documentation"),
            "props": [(p.get("key"), p.get("value")) for p in e.findall("property")],
            "origen": e.get("source"), "destino": e.get("target"),
            "acceso": e.get("accessType") if tipo == "archimate:AccessRelationship" else None,
            "union": e.get("type") if tipo == "archimate:Junction" else None,
        }
    return {"id": raiz.get("id"), "nombre": raiz.get("name"), "conceptos": conceptos, "vistas": vistas}


# Cada aspecto: (nombre, función cruda, función normalizada, solo para relaciones de acceso)
ASPECTOS = [
    ("tipo", lambda c: c["tipo"], lambda c: leer.tipo_normal(c["tipo"], c["union"]), False),
    ("nombre", lambda c: c["nombre"], lambda c: c["nombre"] or "", False),
    ("documentación", lambda c: c["doc"], lambda c: leer.texto_normal(c["doc"]), False),
    ("propiedades (clave, valor y orden)", lambda c: c["props"], lambda c: leer.props_normales(c["props"]), False),
    ("origen y destino", lambda c: (c["origen"], c["destino"]), lambda c: (c["origen"], c["destino"]), False),
    ("tipo de acceso", lambda c: c["acceso"], lambda c: leer.acceso_normal(c["acceso"]), True),
]


def comparar(a: dict, x: dict, etiqueta: str) -> int:
    print(f"\n=== A contra {etiqueta}")
    fallas = 0
    for k in ("id", "nombre"):
        print(f"  {k} del modelo: A={a[k]} {etiqueta}={x[k]}{'' if a[k] == x[k] else '  <-- DIFERENTE'}")
        fallas += a[k] != x[k]
    ids_a, ids_x = set(a["conceptos"]), set(x["conceptos"])
    for clase in ("elemento", "relacion"):
        na = sum(1 for c in a["conceptos"].values() if c["clase"] == clase)
        nx = sum(1 for c in x["conceptos"].values() if c["clase"] == clase)
        print(f"  total {clase}s: A={na} {etiqueta}={nx}{'' if na == nx else '  <-- DIFERENTE'}")
        fallas += na != nx
    print(f"  total vistas: A={len(a['vistas'])} {etiqueta}={len(x['vistas'])}")
    fallas += len(a["vistas"]) != len(x["vistas"])
    faltan, sobran = sorted(ids_a - ids_x), sorted(ids_x - ids_a)
    print(f"  IDs: faltan en {etiqueta}={len(faltan)} sobran en {etiqueta}={len(sobran)}"
          + (f"  ej. {(faltan + sobran)[:3]}" if faltan or sobran else ""))
    fallas += bool(faltan or sobran)

    comunes = sorted(ids_a & ids_x)
    print(f"  {'aspecto':38} {'crudo':>6} {'normal':>7}  ejemplo de diferencia en crudo")
    for nombre, crudo, normal, solo_acceso in ASPECTOS:
        ids = [i for i in comunes if not solo_acceso or leer.tipo_corto(a["conceptos"][i]["tipo"]) == "Access"]
        d_crudo = [i for i in ids if crudo(a["conceptos"][i]) != crudo(x["conceptos"][i])]
        d_normal = [i for i in ids if normal(a["conceptos"][i]) != normal(x["conceptos"][i])]
        ej = ""
        if d_crudo:
            i = d_crudo[0]
            ej = f"{i}: A={crudo(a['conceptos'][i])!r:.70} | {etiqueta}={crudo(x['conceptos'][i])!r:.70}"
        print(f"  {nombre:38} {len(d_crudo):>6} {len(d_normal):>7}  {ej}")
        for i in d_normal[:3]:
            print(f"      NORMALIZADO DIFERENTE {i}: A={normal(a['conceptos'][i])!r:.120}")
            print(f"                            {etiqueta}={normal(x['conceptos'][i])!r:.120}")
        fallas += len(d_normal)

    # Vistas: el generador no las usa; se revisa que estén las mismas cajas y líneas.
    dv = Counter()
    for vid in sorted(set(a["vistas"]) & set(x["vistas"])):
        va, vx = a["vistas"][vid], x["vistas"][vid]
        for k in ("nombre", "nodos", "refs", "conexiones"):
            if va[k] != vx[k]:
                dv[k] += 1
                if dv[k] == 1:
                    print(f"      vista {va['nombre']}: {k} A={str(va[k])[:80]} {etiqueta}={str(vx[k])[:80]}")
    print(f"  vistas (nombre, cajas, elementos en cajas, líneas): diferencias {dict(dv) or 'ninguna'}")
    if "avisos" in x:
        tipos = Counter(m.split(":")[0] for m in x["avisos"])
        print(f"  avisos de pyArchimate al leer: {len(x['avisos'])} {dict(tipos)}")
        for m in sorted(set(x["avisos"]))[:5]:
            print(f"      {m[:160]}")
    return fallas


def main():
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    ruta_archimate, ruta_xml = sys.argv[1], sys.argv[2]
    a = crudo_referencia(ruta_archimate)
    b = leer.cargar_crudo(ruta_archimate)
    c = leer.cargar_crudo(ruta_xml)
    print(f"Modelo: {a['nombre']} ({a['id']})")
    fb = comparar(a, b, "B")
    fc = comparar(a, c, "C")
    print(f"\nRESULTADO: B {'igual' if fb == 0 else 'DIFERENTE'} a A; C {'igual' if fc == 0 else 'DIFERENTE'} a A "
          "(después de normalizar; las vistas cuentan solo por cajas y líneas).")
    sys.exit(0 if fc == 0 else 1)


if __name__ == "__main__":
    main()
