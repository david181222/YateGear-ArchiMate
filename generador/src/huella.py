"""Huella (SHA-256) de la salida del generador, para comprobar que es determinista.

Recorre todos los archivos de la carpeta, salvo bin/, obj/ y el XML exportado
(intermedio/YateGear.xml, que no se versiona). La huella total se calcula sobre la
lista ordenada "ruta  huella" de todos los archivos.

uso:
  python src/huella.py <carpeta>              huella total y número de archivos
  python src/huella.py <carpeta> --detalle    además, la huella de cada archivo
  python src/huella.py <carpeta A> <carpeta B>  compara: lista lo que difiere; código 1 si difieren
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

EXCLUIDOS = {"bin", "obj"}
XML_EXPORTADO = "intermedio/YateGear.xml"


def huellas(carpeta: Path) -> dict[str, str]:
    out = {}
    for p in sorted(carpeta.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(carpeta).as_posix()
        if EXCLUIDOS & set(rel.split("/")) or rel == XML_EXPORTADO:
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def total(h: dict[str, str]) -> str:
    return hashlib.sha256("".join(f"{r}  {x}\n" for r, x in sorted(h.items())).encode("utf-8")).hexdigest()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) == 1:
        h = huellas(Path(args[0]))
        if "--detalle" in sys.argv:
            for r, x in sorted(h.items()):
                print(f"{x}  {r}")
        print(f"Huella total: {total(h)}  ({len(h)} archivos)")
    elif len(args) == 2:
        a, b = huellas(Path(args[0])), huellas(Path(args[1]))
        print(f"A: {total(a)}  ({len(a)} archivos)  {args[0]}")
        print(f"B: {total(b)}  ({len(b)} archivos)  {args[1]}")
        diferentes = sorted(r for r in set(a) | set(b) if a.get(r) != b.get(r))
        for r in diferentes:
            estado = "solo en A" if r not in b else "solo en B" if r not in a else "contenido distinto"
            print(f"  DIFERENTE ({estado}): {r}")
        print("Iguales." if not diferentes else f"{len(diferentes)} archivo(s) diferentes.")
        sys.exit(1 if diferentes else 0)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
