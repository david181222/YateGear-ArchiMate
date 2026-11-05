"""Ejecuta los escenarios de escenarios.json contra la aplicación y marca cada paso con ✓ o ✗.

Cómo se juzga cada paso (lo esperado sale de "espera" en el YAML):
  - sin espera: la respuesta es 2xx;
  - un código: la respuesta tiene ese código;
  - un evento: la respuesta es 2xx y la bitácora registró ese evento para la raíz del escenario
    durante ese paso (así se ven también los eventos que publica una política);
  - {dato: valor, ...}: la respuesta es 2xx y la consulta devuelve esos valores.
En cada paso que crea una raíz y debe responder con éxito se revisa además que reciba la identidad esperada.

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


def igual(a, b) -> bool:
    """Compara un valor de la respuesta con el esperado; los números, por su valor (5 == 5.0)."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) < 1e-9
    return a == b


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
            ident = p.get("identidad")
            eventos = [n["nombre"] for n in nuevos if n["tipo"] == "evento" and (n["datos"] or {}).get("identidad") == ident]
            esp, exito = p["espera"], 200 <= codigo < 300
            if esp["tipo"] == "exito":
                ok = exito
            elif esp["tipo"] == "codigo":
                ok = codigo == esp["valor"]
            elif esp["tipo"] == "evento":
                ok = exito and esp["valor"] in eventos
            else:
                ok = exito and isinstance(cuerpo, dict) and all(igual(cuerpo.get(k), v) for k, v in esp["valores"].items())
            detalle = f"HTTP {codigo}"
            if p["crea"] and exito and isinstance(cuerpo, dict):
                detalle += f' {cuerpo.get("identidad")}'
                if cuerpo.get("identidad") != ident:
                    ok = False
                    detalle += f' (se esperaba {ident})'
            if p["tipo"] == "consulta" and exito and isinstance(cuerpo, dict):
                mostrar = esp["valores"] if esp["tipo"] == "salida" else {k: v for k, v in cuerpo.items() if k == "estado"}
                detalle += "".join(f" {k} {cuerpo.get(k)}" for k in mostrar)
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
