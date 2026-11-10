"""Genera la solución C# desde modelo-ddd.json y los YAML de especificaciones, uno por contexto.

Cada contexto con YAML es un proyecto (biblioteca) con su registro: servicios, políticas y
endpoints. Un proyecto host, con el nombre del modelo, los levanta todos en un solo programa,
y el proyecto Integracion tiene el bus entre contextos (D1): los eventos viajan por nombre y
en JSON, y ningún contexto referencia a otro. Los contextos sin YAML no se generan.

Primero revisa cada YAML con specs.py; si hay errores, no genera nada.
Escribe:
  - los archivos generados (.g.cs, los de proyecto, pruebas y contextos.json), siempre;
  - los archivos manuales (.cs), solo si no existen;
  - trazabilidad/<Proyecto>.csv, uno por contexto;
  - pruebas/EntreContextos/, si entre los YAML hay escenarios entre contextos (S4).
Borra los archivos generados que ya no corresponden y avisa de los manuales huérfanos.

uso: python src/generar.py <modelo-ddd.json> <carpeta de salida> <specs.yaml> [<specs.yaml> ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from comun import nombres
from generacion.csharp import ErrorDeGeneracion
from generacion.solucion import Solucion
from validacion import carga, valores
from validacion.contratos import revisar_contratos
from validacion.entre_contextos import RevisorEntreContextos
from validacion.revisor import Revisor

def main():
    for f in (sys.stdout, sys.stderr):
        f.reconfigure(encoding="utf-8")
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    ruta_json, ruta_salida, *rutas_yaml = sys.argv[1:]
    modelo = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
    specs_, errores, entre, revisores = [], [], [], {}
    for ruta_yaml in rutas_yaml:
        try:
            spec = carga.cargar_yaml(ruta_yaml)
        except Exception as e:                              # YAML mal escrito o clave repetida
            sys.exit(f"ERROR al leer {ruta_yaml}: {e}")
        if valores.es_entre_contextos(spec):                  # escenarios entre contextos (S4): se revisan al final
            entre.append((ruta_yaml, spec))
            continue
        rev = Revisor(modelo, spec, ruta_yaml)
        rev.revisar()
        errores += [f"{ruta_yaml}: {e}" for e in rev.errores]
        specs_.append(spec)
        if not rev.errores:
            revisores[spec["contexto"]] = rev
    for ruta_yaml, spec in entre:
        rev = RevisorEntreContextos(modelo, spec, ruta_yaml, revisores)
        rev.revisar()
        errores += [f"{ruta_yaml}: {e}" for e in rev.errores]
    if not errores:                                         # contratos entre contextos (D2)
        err_c, av_c = revisar_contratos(modelo, revisores)
        errores += [f"contratos entre contextos: {e}" for e in err_c]
        for a in av_c:
            print("AVISO contratos entre contextos:", a)
    if errores:
        print(f"Los YAML no cumplen con el modelo ({len(errores)} error(es)); no se generó nada:", file=sys.stderr)
        for e in errores:
            print("  ERROR", e, file=sys.stderr)
        sys.exit(1)
    try:
        res = Solucion(modelo, specs_, Path(ruta_salida), [s for _, s in entre]).generar()
    except (ErrorDeGeneracion, nombres.NombreInvalido) as e:
        sys.exit(f"ERROR de generación: {e}")
    generados = {n for n, _, _ in res["contextos"]}
    for ctx in modelo["contextos"]:
        if ctx["nombre"] not in generados:
            print(f'Sin YAML (no se genera): {ctx["nombre"]}')
    for nombre, proyecto, filas in res["contextos"]:
        print(f"Generado: {nombre} -> {proyecto} ({filas} filas de trazabilidad)")
    print(f"Archivos generados: {res['escritos']}")
    print(f"Manuales creados: {len(res['creados'])}; conservados sin tocar: {len(res['conservados'])}")
    for x in res["creados"]:
        print("  creado:", x)
    for x in res["borrados"]:
        print("  borrado (generado que ya no corresponde):", x)
    for x in res["huerfanos"]:
        print("  AVISO manual huérfano (no se borra ni se compila; revísalo):", x)
    for ctx_nombre, a in res["avisos_escenarios"]:
        print(f"  AVISO {ctx_nombre}, {a}")
    for x in res["sueltas"]:
        print(f"  AVISO {x}/ tiene código a mano de un contexto que ya no se genera (no se borra ni se compila; revísalo)")


if __name__ == "__main__":
    main()
