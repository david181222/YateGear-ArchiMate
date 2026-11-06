"""Revisa que la trazabilidad de cada contexto generado tenga todos sus elementos.

Los contextos generados y su trazabilidad/<Proyecto>.csv salen de contextos.json.
  - Cada ID ArchiMate del contexto en modelo-ddd.json (elementos y relaciones) tiene al
    menos una fila en su CSV. No cuenta "otros_contextos": esos eventos son de otros
    contextos y no se generan en este.
  - Cada archivo que nombra el CSV existe en la carpeta de salida.

Termina con código 1 si falta algo.

uso: python src/revisar_trazabilidad.py <modelo-ddd.json> <carpeta de salida>
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ID = re.compile(r"id-[0-9a-f]{32}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    modelo = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    salida = Path(sys.argv[2])
    generados = json.loads((salida / "contextos.json").read_text(encoding="utf-8"))["contextos"]
    ctxs = {c["nombre"]: c for c in modelo["contextos"]}

    faltan_ids, faltan_archivos, filas = [], [], []
    for g in generados:
        with open(salida / g["trazabilidad"], encoding="utf-8", newline="") as f:
            filas_ctx = list(csv.DictReader(f))
        filas += filas_ctx
        sin_otros = {k: v for k, v in ctxs[g["nombre"]].items() if k != "otros_contextos"}
        ids = set(ID.findall(json.dumps(sin_otros)))
        en_csv = {f["ID ArchiMate"] for f in filas_ctx}
        faltan_ids += [f'{i} ({g["trazabilidad"]})' for i in sorted(ids - en_csv)]
        print(f'{g["nombre"]}: {len(ids)} IDs en modelo-ddd.json; {len(ids & en_csv)} con fila en {g["trazabilidad"]}')
        for f in filas_ctx:
            if not (salida / f["archivo generado"]).is_file():
                faltan_archivos.append(f["archivo generado"])

    tipos = Counter(f["tipo"] for f in filas)
    print(f"{len(filas)} filas, por tipo: " + ", ".join(f"{t} {n}" for t, n in sorted(tipos.items())))
    for i in faltan_ids:
        print("  FALTA en la trazabilidad:", i)
    for a in sorted(set(faltan_archivos)):
        print("  NO EXISTE el archivo:", a)
    if faltan_ids or faltan_archivos:
        sys.exit(1)
    print("Todos los elementos de los contextos generados están en su trazabilidad y todos sus archivos existen.")


if __name__ == "__main__":
    main()
