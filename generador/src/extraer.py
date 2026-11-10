"""Extrae los contextos del modelo ArchiMate y escribe modelo-ddd.json.

Todo se busca por tipo y por relación del modelo, nunca por nombre. Un contexto es
un componente de aplicación al que se le asigna al menos un proceso de aplicación
con la propiedad "Código del servicio" (o "Servicio básico V4", el nombre que usa el modelo
de YateGear). Nunca se leen los anidamientos de las vistas.

Sin nombres de contexto, extrae todos. Con nombres, solo esos (los demás quedan
como "otros_contextos" de cada uno, igual que siempre).

Si una validación falla, junta todos los errores, los muestra y termina con
código 1 sin escribir el JSON.

uso: python src/extraer.py <modelo.xml | modelo.archimate> <salida.json> ["<Contexto ...>" ...]
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

from lectura import leer
from lectura.extractor import NOMBRE_SB, Extractor, resumen


def main():
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ruta_modelo, ruta_json, *nombres_ctx = sys.argv[1:]
    g = leer.leer(ruta_modelo)
    ex = Extractor(g)
    nombres_ctx = nombres_ctx or ex.contextos()
    if not nombres_ctx:
        ex.error("contexto", "el modelo no tiene contextos: ningún componente de aplicación tiene asignado un proceso "
                             f"con la propiedad {NOMBRE_SB}")
    ctxs = [ex.extraer(n) for n in nombres_ctx]
    for a in ex.avisos:
        print("AVISO:", a)
    if ex.errores:
        print(f"\nSe encontraron {len(ex.errores)} error(es); no se escribió {ruta_json}:", file=sys.stderr)
        for e in ex.errores:
            print("  ERROR", e, file=sys.stderr)
        sys.exit(1)
    salida = {
        "generado_desde": {"modelo_id": g.id, "modelo_nombre": g.nombre, "archivo": Path(ruta_modelo).name},
        "contextos": ctxs,
    }
    texto = json.dumps(salida, ensure_ascii=False, indent=2) + "\n"
    Path(ruta_json).write_bytes(texto.encode("utf-8"))      # UTF-8 sin BOM y fin de línea LF
    for ctx in ctxs:
        print("\n".join(resumen(ctx)))
    print(f"\nEscrito: {ruta_json}")


if __name__ == "__main__":
    main()
