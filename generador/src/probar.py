"""Ejecuta los escenarios de escenarios.json contra la aplicación y marca cada paso con ✓ o ✗.

Cómo se juzga cada paso (lo esperado sale de "espera" en el YAML):
  - sin espera: la respuesta es 2xx;
  - un código: la respuesta tiene ese código;
  - un evento: la respuesta es 2xx y la bitácora registró ese evento para la raíz del escenario
    durante ese paso (así se ven también los eventos que publica una política);
  - {dato: valor, ...}: la respuesta es 2xx y la consulta devuelve esos valores.
  - en los escenarios entre contextos (S4), una lista de eventos y de envíos de los SA: la respuesta es 2xx, y
    durante el paso pasaron por el bus entre contextos todos esos eventos (de cualquier contexto) y la bitácora
    del contexto que envía registró esos envíos.
En los escenarios entre contextos, además, un paso falla si durante él falló un suscriptor del bus (GET
/eventos-entre-contextos, "errores"): así "ningún error en el bus" lo comprueba la prueba.
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
    """Compara un valor de la respuesta con el esperado; los números, por su valor (5 == 5.0); una lista con un
    número, por cuántos elementos tiene."""
    if isinstance(a, list) and isinstance(b, int) and not isinstance(b, bool):
        return len(a) == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) < 1e-9
    return a == b


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        esc = json.load(f)
    raiz_url = sys.argv[2].rstrip("/")
    base = raiz_url + esc["ruta_base"]
    entre = bool(esc.get("entre_contextos"))           # escenarios de punta a punta entre contextos (S4)

    def bitacora(ruta_base=esc["ruta_base"]):
        return llamar("GET", f"{raiz_url}{ruta_base}/bitacora", None)[1]

    def bus():                                         # los eventos que pasaron por el bus y los errores de sus suscriptores
        return llamar("GET", f"{raiz_url}/eventos-entre-contextos", None)[1]

    total = fallas = 0
    errores_bus = []
    for e in esc["escenarios"]:
        print(f'\nEscenario "{e["nombre"]}"' + (f' ({e["identidad"]})' if e["identidad"] else ""))
        for p in e["pasos"]:
            total += 1
            if entre:
                b = bus()
                antes_bus, antes_err = len(b["eventos"]), len(b["errores"])
                antes_ctx = {r: len(bitacora(r)) for r in esc["contextos"]}
            else:
                antes = len(bitacora())
            codigo, cuerpo = llamar(p["metodo"], base + p["ruta"], p["cuerpo"])
            ident = p.get("identidad")
            nuevos_err = []
            if entre:
                # Entre contextos, los eventos de cualquier contexto (los publica el bus) y los envíos de los SA (G11).
                b = bus()
                eventos = [x["evento"] for x in b["eventos"][antes_bus:]]
                # Un suscriptor que falla no deshace el paso (GEN-SUP-04), pero el recorrido ya no es el esperado:
                # el paso falla y se muestra el error.
                nuevos_err = b["errores"][antes_err:]
                errores_bus += nuevos_err
                enviados = {(r, n["nombre"]) for r in esc["contextos"] for n in bitacora(r)[antes_ctx[r]:]
                            if n["tipo"] == "envío por servicio SA"}
            else:
                nuevos = bitacora()[antes:]
                # Los eventos de la raíz del paso; un paso sin identidad (un comando sobre todas las raíces) acepta los de cualquiera.
                eventos = [n["nombre"] for n in nuevos if n["tipo"] == "evento" and (ident is None or (n["datos"] or {}).get("identidad") == ident)]
                enviados = set()
            esp, exito = p["espera"], 200 <= codigo < 300
            if esp["tipo"] == "exito":
                ok = exito
            elif esp["tipo"] == "codigo":             # y, si los dice, los campos de la respuesta de error
                ok = codigo == esp["valor"] and all(isinstance(cuerpo, dict) and cuerpo.get(k) == v
                                                    for k, v in (esp.get("campos") or {}).items())
            elif esp["tipo"] == "evento":
                ok = exito and esp["valor"] in eventos
            elif esp["tipo"] == "eventos":             # entre contextos: todos los eventos y envíos de la lista
                ok = exito and all(x in eventos for x in esp["eventos"]) and \
                    all((x["ruta_base"], x["nombre"]) in enviados for x in esp["envios"])
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
            if enviados:
                detalle += " envíos: " + ", ".join(sorted(n for _, n in enviados))
            if not exito and isinstance(cuerpo, dict):
                detalle += " " + json.dumps(cuerpo, ensure_ascii=False)
            if nuevos_err:
                ok = False
                detalle += "  <-- error en el bus: " + "; ".join(nuevos_err)
            if not ok:
                fallas += 1
                if not nuevos_err:
                    detalle += f'  <-- se esperaba {esp["texto"]}'
            print(f'  {"✓" if ok else "✗"} {p["numero"]:>2}. {p["nombre"]:<40} {detalle}')
    if entre:
        print(f"\nErrores en el bus entre contextos: {len(errores_bus)}.")
    print(f"\n{total} pasos: {total - fallas} bien, {fallas} con falla.")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
