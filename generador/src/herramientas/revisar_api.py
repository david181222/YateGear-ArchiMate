"""Revisa la documentación de la API de la aplicación levantada: el documento OpenAPI y la página Swagger.

Comprueba que:
  - GET /openapi/v1.json responde 200 con un documento OpenAPI;
  - cada contexto de contextos.json tiene endpoints en el documento, bajo su ruta;
  - cada endpoint tiene resumen (de qué elemento del modelo sale) y etiqueta (su contexto);
  - GET /swagger/index.html responde 200.

Termina con código 1 si algo falla. Lo usa probar.ps1, que levanta y detiene la aplicación.

uso: python src/herramientas/revisar_api.py <contextos.json> <url de la aplicación, p. ej. http://localhost:5080>
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def pedir(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        return 0, str(e.reason).encode()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        manifiesto = json.load(f)
    url = sys.argv[2].rstrip("/")
    fallas = []

    codigo, cuerpo = pedir(f"{url}/openapi/v1.json")
    if codigo != 200:
        fallas.append(f"GET /openapi/v1.json respondió {codigo}")
        rutas = {}
    else:
        documento = json.loads(cuerpo)
        rutas = documento.get("paths") or {}
        if not documento.get("openapi"):
            fallas.append("/openapi/v1.json no es un documento OpenAPI")
    operaciones = [(ruta, metodo, op) for ruta, metodos in rutas.items() for metodo, op in metodos.items()]
    for ctx in manifiesto["contextos"]:
        suyas = [r for r, _, _ in operaciones if r.startswith(ctx["ruta_base"] + "/")]
        if not suyas:
            fallas.append(f'{ctx["nombre"]} no tiene endpoints en el documento (bajo {ctx["ruta_base"]})')
        else:
            print(f'  ✓ {ctx["nombre"]}: {len(suyas)} endpoints')
    for ruta, metodo, op in operaciones:
        if not op.get("summary") or not op.get("tags"):
            fallas.append(f"{metodo.upper()} {ruta} no tiene resumen o etiqueta")

    codigo, _ = pedir(f"{url}/swagger/index.html")
    if codigo != 200:
        fallas.append(f"GET /swagger/index.html respondió {codigo}")
    else:
        print(f"  ✓ Swagger: {url}/swagger")

    for x in fallas:
        print(f"  ✗ {x}")
    print(f"{len(operaciones)} endpoints en el documento OpenAPI: {'sin fallas' if not fallas else f'{len(fallas)} falla(s)'}.")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
