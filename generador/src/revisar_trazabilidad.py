"""Revisa que trazabilidad.csv tenga todos los elementos del contexto.

  - Cada ID ArchiMate del contexto en modelo-ddd.json (elementos y relaciones) tiene al
    menos una fila en trazabilidad.csv. No cuenta "otros_contextos": esos eventos son de
    otros contextos y aquí no se generan.
  - Cada archivo que nombra trazabilidad.csv existe en la carpeta de salida.

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
    with open(salida / "trazabilidad.csv", encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))

    faltan_ids, faltan_archivos = [], []
    for ctx in modelo["contextos"]:
        sin_otros = {k: v for k, v in ctx.items() if k != "otros_contextos"}
        ids = set(ID.findall(json.dumps(sin_otros)))
        en_csv = {f["ID ArchiMate"] for f in filas}
        faltan_ids += sorted(ids - en_csv)
        print(f'{ctx["nombre"]}: {len(ids)} IDs en modelo-ddd.json; {len(ids & en_csv)} con fila en trazabilidad.csv')
    for f in filas:
        if not (salida / f["archivo generado"]).is_file():
            faltan_archivos.append(f["archivo generado"])

    tipos = Counter(f["tipo"] for f in filas)
    print(f"{len(filas)} filas, por tipo: " + ", ".join(f"{t} {n}" for t, n in sorted(tipos.items())))
    for i in faltan_ids:
        print("  FALTA en trazabilidad.csv:", i)
    for a in sorted(set(faltan_archivos)):
        print("  NO EXISTE el archivo:", a)
    if faltan_ids or faltan_archivos:
        sys.exit(1)
    print("Todos los elementos del contexto están en trazabilidad.csv y todos sus archivos existen.")


if __name__ == "__main__":
    main()
