"""Pruebas del validador (specs.py): cada caso rompe a propósito un YAML y comprueba que specs.py lo detecte.

Primero revisa que los YAML de la carpeta de cada caso, sin cambios, no den errores (si no, los casos no prueban nada).
Después, por cada caso de casos.yaml: carga su YAML base, le aplica los cambios en memoria (no toca el archivo), lo
revisa como lo hacen specs.py y generar.py (el YAML, los contratos entre contextos con los demás YAML de su carpeta y,
si es el de escenarios entre contextos, sus escenarios) y comprueba que salga un error con el texto esperado.

Formato de un caso (las rutas de base son relativas a la carpeta del generador):

  - caso: un comando declara un evento que en el modelo no dispara
    base: specs/cobros-y-deposito.yaml
    cambia: [comandos, Bloquear el depósito, eventos]     # claves, o posiciones de una lista (0, 1, ...)
    valor: [Depósito liberado]
    error: 'el YAML declara "Depósito liberado"'

En lugar de cambia y valor: quita: [ruta] borra esa clave o ese elemento; y cambios: [{cambia, valor} o {quita}, ...]
hace varios cambios en el mismo caso.

Cada clave nueva del YAML trae su caso: así se sabe que specs.py de verdad la revisa.

Termina con código 1 si algún caso no sale como se espera.

uso: python src/probar_validador.py <modelo-ddd.json> <casos.yaml>
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import specs

RAIZ = Path(__file__).resolve().parent.parent          # la carpeta del generador


def ubicar(x, ruta: list, donde: str):
    """El contenedor del último paso de la ruta y su clave."""
    for paso in ruta[:-1]:
        try:
            x = x[paso]
        except (KeyError, IndexError, TypeError):
            raise ValueError(f'{donde}: la ruta no existe en el YAML base (falla en "{paso}")')
    return x, ruta[-1]


def aplicar(spec, cambios: list[dict], donde: str):
    for c in cambios:
        if "quita" in c:
            cont, k = ubicar(spec, c["quita"], donde)
            try:
                del cont[k]
            except (KeyError, IndexError, TypeError):
                raise ValueError(f'{donde}: no hay nada que quitar en {c["quita"]}')
        else:
            cont, k = ubicar(spec, c["cambia"], donde)
            if isinstance(cont, list) and not isinstance(k, int):
                raise ValueError(f'{donde}: en una lista la posición es un número')
            cont[k] = c["valor"]


def revisar(modelo: dict, ruta: Path, spec, sanos: dict[str, specs.Revisor]) -> list[str]:
    """Los errores de un YAML (ya cambiado), revisado como lo hacen specs.py y generar.py."""
    if specs.es_entre_contextos(spec):
        rev = specs.RevisorEntreContextos(modelo, spec, str(ruta), sanos)
        rev.revisar()
        return rev.errores
    rev = specs.Revisor(modelo, spec, str(ruta))
    rev.id_nombre = ""
    rev.revisar()
    if rev.errores or not isinstance(spec, dict):
        return rev.errores
    otros = {k: v for k, v in sanos.items() if k != spec.get("contexto")}
    otros[spec["contexto"]] = rev
    errores, _ = specs.revisar_contratos(modelo, otros, solo=spec["contexto"])
    return errores


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    modelo = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    casos = specs.cargar_yaml(sys.argv[2]) or []

    # Los YAML sin cambios de cada carpeta de los casos: sin errores, y sus revisores para los contratos entre contextos.
    carpetas = sorted({(RAIZ / c["base"]).parent for c in casos if isinstance(c, dict) and "base" in c})
    sanos_por_carpeta, fallas = {}, 0
    for carpeta in carpetas:
        rutas = sorted(str(p) for p in carpeta.glob("*.yaml"))
        sanos, errores = specs.revisores_de_contextos(modelo, rutas)
        for r in rutas:
            spec = specs.cargar_yaml(r)
            if specs.es_entre_contextos(spec):
                errores += revisar(modelo, Path(r), spec, sanos)
        errores += specs.revisar_contratos(modelo, sanos)[0]
        if errores:
            print(f"Los YAML de {carpeta.name}/ ya tienen errores sin cambiarlos: los casos no prueban nada.")
            for e in errores:
                print("  ERROR", e)
            sys.exit(1)
        sanos_por_carpeta[carpeta] = sanos
    print(f"Los YAML de {', '.join(c.name + '/' for c in carpetas)} no tienen errores sin cambios.\n")

    for i, c in enumerate(casos, 1):
        donde = f'caso {i} ("{c.get("caso", "?")}")' if isinstance(c, dict) else f"caso {i}"
        try:
            if not isinstance(c, dict) or not {"caso", "base", "error"} <= set(c):
                raise ValueError(f"{donde}: un caso tiene caso, base, error y cambia/valor, quita o cambios")
            cambios = c.get("cambios") or ([{"cambia": c["cambia"], "valor": c.get("valor")}] if "cambia" in c else
                                           [{"quita": c["quita"]}] if "quita" in c else [])
            if not cambios:
                raise ValueError(f"{donde}: no dice qué cambiar (cambia y valor, quita o cambios)")
            ruta = RAIZ / c["base"]
            spec = copy.deepcopy(specs.cargar_yaml(str(ruta)))
            aplicar(spec, cambios, donde)
            errores = revisar(modelo, ruta, spec, sanos_por_carpeta[ruta.parent])
        except ValueError as e:
            fallas += 1
            print(f"  ✗ {i:>2}. {c.get('caso', '?') if isinstance(c, dict) else '?'}\n       {e}")
            continue
        ok = any(c["error"] in e for e in errores)
        if not ok:
            fallas += 1
        print(f'  {"✓" if ok else "✗"} {i:>2}. {c["caso"]}')
        if not ok:
            print(f'       se esperaba un error con: {c["error"]}')
            for e in errores[:5] or ["(ningún error: specs.py no lo detecta)"]:
                print(f"       salió: {e}")
    print(f"\n{len(casos)} casos: {len(casos) - fallas} bien, {fallas} con falla.")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
