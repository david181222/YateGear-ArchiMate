"""Ejecuta los escenarios de escenarios.json contra la aplicación y marca cada paso con ✓ o ✗.

Cómo se juzga cada paso (lo esperado sale de "espera" en el YAML):
  - sin espera: la respuesta es 2xx;
  - un código: la respuesta tiene ese código;
  - un evento: la respuesta es 2xx y la bitácora registró ese evento para la raíz del escenario
    durante ese paso (así se ven también los eventos que publica una política);
  - {estado: ...}: la respuesta es 2xx y la consulta devuelve ese estado.
En el primer paso de cada escenario se revisa además que la raíz reciba la identidad esperada.

Termina con código 1 si algún paso falla. Lo usa probar.ps1, que levanta y detiene la aplicación.

uso: python src/probar.py <escenarios.json> <url de la aplicación, p. ej. http://localhost:5080>
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def llamar(metodo: str, url: str, cuerpo) -> tuple[int, object]:
    datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8") if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"} if datos else {})
    try:
        r = urllib.request.urlopen(req, timeout=15)
        codigo, texto = r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        codigo, texto = e.code, e.read().decode("utf-8")
    try:
        return codigo, json.loads(texto) if texto else None
    except json.JSONDecodeError:
        return codigo, texto


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        esc = json.load(f)
    base = sys.argv[2].rstrip("/") + esc["ruta_base"]

    def bitacora():
        return llamar("GET", f"{base}/bitacora", None)[1]

    total = fallas = 0
    for e in esc["escenarios"]:
        print(f'\nEscenario "{e["nombre"]}" ({e["identidad"]})')
        for p in e["pasos"]:
            total += 1
            antes = len(bitacora())
            codigo, cuerpo = llamar(p["metodo"], base + p["ruta"], p["cuerpo"])
            nuevos = bitacora()[antes:]
            eventos = [n["nombre"] for n in nuevos if n["tipo"] == "evento" and (n["datos"] or {}).get("identidad") == e["identidad"]]
            esp, exito = p["espera"], 200 <= codigo < 300
            if esp["tipo"] == "exito":
                ok = exito
            elif esp["tipo"] == "codigo":
                ok = codigo == esp["valor"]
            elif esp["tipo"] == "evento":
                ok = exito and esp["valor"] in eventos
            else:
                ok = exito and isinstance(cuerpo, dict) and cuerpo.get("estado") == esp["json"]
            detalle = f"HTTP {codigo}"
            if p["crea"] and isinstance(cuerpo, dict):
                detalle += f' {cuerpo.get("identidad")}'
                if cuerpo.get("identidad") != e["identidad"]:
                    ok = False
                    detalle += f' (se esperaba {e["identidad"]})'
            if p["tipo"] == "consulta" and isinstance(cuerpo, dict) and "estado" in cuerpo:
                detalle += f' estado {cuerpo["estado"]}'
            if eventos:
                detalle += " eventos: " + ", ".join(eventos)
            if not exito and isinstance(cuerpo, dict):
                detalle += " " + json.dumps(cuerpo, ensure_ascii=False)
            if not ok:
                fallas += 1
                detalle += f'  <-- se esperaba {esp["texto"]}'
            print(f'  {"✓" if ok else "✗"} {p["numero"]:>2}. {p["nombre"]:<40} {detalle}')
    print(f"\n{total} pasos: {total - fallas} bien, {fallas} con falla.")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
