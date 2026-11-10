"""Contratos entre contextos: lo que un contexto recibe debe llegar como lo publica el otro."""
from __future__ import annotations

from comun import tipos
from validacion.valores import mismo_tipo

from validacion.revisor import Revisor

def revisar_contratos(modelo: dict, revisores: dict[str, Revisor], solo: str | None = None) -> tuple[list[str], list[str]]:
    """Contratos entre contextos (D2): lo que quien recibe un evento de otro contexto declara en
    eventos_de_otros_contextos debe llegar en ese evento tal como lo publica el YAML del contexto que lo publica.

    Por cada evento: el dato con que llega (identidad) y cada dato de datos están entre los que publica (la identidad
    de su raíz, datos y calculados), con el mismo tipo; y un dato obligatorio para quien recibe no es opcional para
    quien publica (podría llegar en null). Quien publica puede mandar más datos de los que se reciben.
    Con solo, revisa únicamente los pares en que está ese contexto. Devuelve (errores, avisos).
    """
    errores, avisos = [], []
    ctxs = {c["nombre"]: c for c in modelo["contextos"]}

    def objetos(nombre_ctx: str) -> dict:
        return {v["nombre"]: {c["nombre"]: c for c in v["campos"]}
                for a in ctxs[nombre_ctx]["agregados"] for v in a["objetos_valor"]}

    def tipo_en(nombre_ctx: str, texto):
        tipos.usar_objetos(objetos(nombre_ctx))    # List<objeto de valor> se interpreta con los del contexto
        try:
            return tipos.interpretar(texto)
        except tipos.TipoInvalido:
            return None                            # el error ya lo dio el Revisor de ese contexto

    def mismo_entre(tr: dict, receptor: str, tp: dict, emisor: str) -> bool:
        """Mismo tipo entre dos contextos: una lista de objetos de valor se compara por sus campos, no por el nombre."""
        if tr["base"] == "objeto" and tp["base"] == "objeto":
            cr, cp = objetos(receptor)[tr["objeto"]], objetos(emisor)[tp["objeto"]]
            return tr["lista"] == tp["lista"] and set(cr) == set(cp) and all(mismo_tipo(cr[k], cp[k]) for k in cr)
        return mismo_tipo(tr, tp)

    for receptor, rv in sorted(revisores.items()):
        ext = rv.s.get("eventos_de_otros_contextos") if isinstance(rv.s.get("eventos_de_otros_contextos"), dict) else {}
        for n, x in sorted(ext.items()):
            if not isinstance(x, dict):
                continue
            emisor = x.get("de")
            if solo and solo not in (receptor, emisor):
                continue
            d = f"{receptor} > eventos_de_otros_contextos > {n}"
            pub = revisores.get(emisor)
            if pub is None:
                avisos.append(f'[{d}] "{emisor}" no tiene YAML (o tiene errores): no se revisa contra lo que publica')
                continue
            ev_y = (pub.s.get("eventos") or {}).get(n)
            ev_m = next((e for e in ctxs[emisor]["eventos"] if e["nombre"] == n), None)
            if not isinstance(ev_y, dict) or ev_m is None or ev_m["agregado_id"] not in pub.raiz_por_agregado:
                continue                                  # lo dice el Revisor de quien publica
            id_pub = pub.raiz_por_agregado[ev_m["agregado_id"]]["id_nombre"]
            publica = {id_pub: tipos.interpretar("string")}
            for k, t in {**(ev_y.get("datos") or {}), **(ev_y.get("calculados") or {})}.items():
                tp = tipo_en(emisor, t)
                if tp:
                    publica[k] = tp
            lista_pub = ", ".join(f'"{k}"' for k in sorted(publica))
            id_rec = rv.identidad_externos.get(n)
            if isinstance(id_rec, str) and id_rec not in publica:
                errores.append(f'[{d} > identidad] llega con "{id_rec}", y "{emisor}" no lo publica en "{n}"; '
                               f"publica: {lista_pub}")
            for k, t in (x.get("datos") or {}).items():
                tr = tipo_en(receptor, t)
                if tr is None:
                    continue
                if k not in publica:
                    errores.append(f'[{d} > datos] "{k}" no llega: "{emisor}" no lo publica en "{n}"; publica: {lista_pub}')
                elif not mismo_entre(tr, receptor, publica[k], emisor):
                    errores.append(f'[{d} > datos] "{k}" se recibe como {tr["tipo"]} y "{emisor}" lo publica como '
                                   f'{publica[k]["tipo"]}')
                elif publica[k]["opcional"] and not tr["opcional"]:
                    errores.append(f'[{d} > datos] "{k}" es obligatorio aquí y "{emisor}" lo publica como opcional '
                                   f'({publica[k]["tipo"]}): puede llegar en null. Recíbelo como {tr["tipo"]}?')
    tipos.usar_objetos({})
    return errores, avisos
