"""Lee un YAML de especificaciones. Una clave repetida es un error."""
from __future__ import annotations

import yaml

class _Cargador(yaml.SafeLoader):
    pass


def _mapa_sin_repetidos(loader, node, deep=False):
    vistas = set()
    for k_node, _ in node.value:
        k = loader.construct_object(k_node, deep=deep)
        if k in vistas:
            raise yaml.constructor.ConstructorError(None, None, f'clave repetida "{k}"', k_node.start_mark)
        vistas.add(k)
    return loader.construct_mapping(node, deep)


_Cargador.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapa_sin_repetidos)


def cargar_yaml(ruta: str):
    with open(ruta, encoding="utf-8") as f:
        return yaml.load(f, Loader=_Cargador)
