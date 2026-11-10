"""Revisa el YAML de especificaciones de un contexto contra modelo-ddd.json.

No genera nada. Junta todos los errores y termina con código 1 si el YAML:
  - deja sin especificar un elemento del contexto o nombra uno que no existe;
  - tiene una clave desconocida o repetida, un tipo no permitido o un estado
    fuera de la lista cerrada;
  - declara para un comando eventos distintos de los que ese comando dispara
    en el modelo (ni más ni menos);
  - usa un dato que no está disponible por su nombre, con el mismo tipo, donde
    se necesita (regla de los datos, ver el comentario al inicio del YAML).

Además revisa los contratos entre contextos (revisar_contratos, D2) contra los YAML de los demás contextos de su
misma carpeta: lo que el YAML declara que recibe de otro contexto debe llegar, con el mismo tipo, en el evento que ese
contexto publica; y lo que publica debe cubrir lo que los demás declaran recibir de él.

Un YAML de escenarios entre contextos (S4, solo con escenarios_entre_contextos) se revisa contra los YAML de
los contextos de su misma carpeta.

uso: python src/specs.py <modelo-ddd.json> <specs.yaml>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from validacion.carga import cargar_yaml
from validacion.contratos import revisar_contratos
from validacion.entre_contextos import RevisorEntreContextos, revisores_de_contextos
from validacion.revisor import Revisor
from validacion.valores import CLAVE_ENTRE_CONTEXTOS, es_entre_contextos

def main():
    for f in (sys.stdout, sys.stderr):
        f.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    ruta_json, ruta_yaml = sys.argv[1:]
    modelo = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
    try:
        spec = cargar_yaml(ruta_yaml)
    except yaml.YAMLError as e:
        sys.exit(f"ERROR al leer {ruta_yaml}: {e}")
    if es_entre_contextos(spec):
        # Escenarios entre contextos: se revisan contra los YAML de contextos de la misma carpeta.
        rutas = sorted(str(p) for p in Path(ruta_yaml).parent.glob("*.yaml") if p.resolve() != Path(ruta_yaml).resolve())
        revisores, errores = revisores_de_contextos(modelo, rutas)
        rev = RevisorEntreContextos(modelo, spec, ruta_yaml, revisores)
        rev.revisar()
        errores += rev.errores
        err_c, av_c = revisar_contratos(modelo, revisores)
        errores += err_c
        for a in av_c:
            print("AVISO", a)
        if errores:
            print(f"\n{len(errores)} error(es) en {ruta_yaml}:", file=sys.stderr)
            for e in errores:
                print("  ERROR", e, file=sys.stderr)
            sys.exit(1)
        n = sum(len(p) for p in spec[CLAVE_ENTRE_CONTEXTOS].values())
        print(f"Escenarios entre contextos: {len(spec[CLAVE_ENTRE_CONTEXTOS])} escenarios, {n} pasos, "
              f"{len(revisores)} contextos con YAML.")
        print(f"\nEl YAML cumple con el modelo y con los YAML de los contextos: {ruta_yaml}")
        return
    rev = Revisor(modelo, spec, ruta_yaml)
    rev.revisar()
    if not rev.errores and isinstance(spec, dict):
        # Contratos entre contextos (D2): contra los YAML de los demás contextos de la misma carpeta. Los que tienen
        # errores no se usan (cada uno los dice cuando se revisa).
        rutas = sorted(str(p) for p in Path(ruta_yaml).parent.glob("*.yaml") if p.resolve() != Path(ruta_yaml).resolve())
        otros, _ = revisores_de_contextos(modelo, rutas)
        otros[spec["contexto"]] = rev
        err_c, av_c = revisar_contratos(modelo, otros, solo=spec["contexto"])
        rev.errores += err_c
        rev.avisos += av_c
    for a in rev.avisos:
        print("AVISO", a)
    if rev.varios_origenes:
        print("Datos que llegan de más de un origen (gana el más reciente: SA, luego entrada, luego raíz):")
        for v in rev.varios_origenes:
            print("  -", v)
    if rev.errores:
        print(f"\n{len(rev.errores)} error(es) en {ruta_yaml}:", file=sys.stderr)
        for e in rev.errores:
            print("  ERROR", e, file=sys.stderr)
        sys.exit(1)
    print("\n".join(rev.resumen()))
    print(f"\nEl YAML cumple con el modelo: {ruta_yaml}")


if __name__ == "__main__":
    main()
