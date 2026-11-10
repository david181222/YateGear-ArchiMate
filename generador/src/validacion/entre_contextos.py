"""Revisión de los escenarios de punta a punta entre contextos."""
from __future__ import annotations

from comun import tipos
from validacion.carga import cargar_yaml
from validacion.revisor import Revisor
from validacion.valores import CAMPOS_DE_ERROR, CLAVE_ENTRE_CONTEXTOS, es_entre_contextos, valor_valido


class RevisorEntreContextos:
    """Revisa los escenarios de punta a punta entre contextos (S4) contra los YAML de los contextos que usan.

    Cada paso es un comando, una consulta o un mensaje de un SA del contexto que dice en (los eventos entre contextos
    llegan por el bus, no se envían a mano); con fija datos de su entrada, y espera es un evento o una lista de eventos
    (de cualquier contexto generado) y de mensajes que envía un SA, un código o datos de una consulta.
    """

    def __init__(self, modelo: dict, spec, nombre_archivo: str, revisores: dict[str, "Revisor"]):
        self.m, self.s, self.archivo, self.revisores = modelo, spec, nombre_archivo, revisores
        self.errores: list[str] = []
        self.avisos: list[str] = []

    def error(self, donde: str, texto: str):
        self.errores.append(f"[{donde}] {texto}")

    def revisar(self):
        s = self.s if isinstance(self.s, dict) else {}
        for k in s:
            if k != CLAVE_ENTRE_CONTEXTOS:
                self.error("archivo", f'clave desconocida "{k}"; un YAML entre contextos solo tiene {CLAVE_ENTRE_CONTEXTOS}')
        esc = s.get(CLAVE_ENTRE_CONTEXTOS)
        if not isinstance(esc, dict) or not esc:
            self.error(CLAVE_ENTRE_CONTEXTOS, "escribe al menos un escenario, con su lista de pasos")
            return
        eventos = {e["nombre"] for c in self.m["contextos"] if c["nombre"] in self.revisores for e in c["eventos"]}
        envios = {n for r in self.revisores.values() for n in getattr(r, "envios_sa", {})}
        codigos = {"comando": {404, 409, 422}, "consulta": {404, 422}, "mensaje de un servicio SA": {404, 409, 422}}
        for nombre_e, pasos in esc.items():
            d = f"{CLAVE_ENTRE_CONTEXTOS} > {nombre_e}"
            if not isinstance(pasos, list) or not pasos:
                self.error(d, "el escenario es una lista de pasos")
                continue
            for i, paso in enumerate(pasos, 1):
                dp = f"{d} > paso {i}"
                if not isinstance(paso, dict) or len(paso) != 1:
                    self.error(dp, 'un paso es "nombre:" con en, con y espera')
                    continue
                nombre, op = next(iter(paso.items()))
                dp = f"{dp} ({nombre})"
                if not isinstance(op, dict):
                    self.error(dp, "falta en: el contexto del paso")
                    continue
                for k in op:
                    if k not in ("en", "con", "espera"):
                        self.error(dp, f'clave desconocida "{k}"; se permiten: en, con, espera')
                rv = self.revisores.get(op.get("en"))
                if rv is None:
                    self.error(f"{dp} > en", f'"{op.get("en")}" no es un contexto con YAML; están: {", ".join(sorted(self.revisores))}')
                    continue
                if nombre in rv.entradas_cmd:
                    tipo, campos = "comando", dict(rv.entradas_cmd[nombre]["entrada"])
                    if not rv.entradas_cmd[nombre]["crea"]:
                        campos.setdefault(rv.raices[rv.entradas_cmd[nombre]["raiz"]]["id_nombre"], tipos.interpretar("string"))
                elif nombre in rv.qs_y:
                    tipo = "consulta"
                    campos = {k: tipos.interpretar(v) for k, v in ((rv.qs_y[nombre] or {}).get("entrada") or {}).items()}
                    if (rv.qs_y[nombre] or {}).get("sobre") != "todas":
                        q_m = next((q for q in rv.ctx["consultas"] if q["nombre"] == nombre), None)
                        raiz_q = (rv.qs_y[nombre] or {}).get("de") or (rv.raiz_por_id[q_m["lee"][0]["raiz_id"]]["nombre"] if q_m else None)
                        if raiz_q in rv.raices:
                            campos.setdefault(rv.raices[raiz_q]["id_nombre"], tipos.interpretar("string"))
                elif nombre in rv.mensajes_sa:
                    tipo, campos = "mensaje de un servicio SA", dict(rv.mensajes_sa[nombre]["datos"])
                elif nombre in rv.ext_y:
                    self.error(dp, f'"{nombre}" es un evento de otro contexto: entre contextos llega solo por el bus (G12)')
                    continue
                else:
                    self.error(dp, f'"{nombre}" no es un comando, una consulta ni un mensaje de un SA de "{op["en"]}"')
                    continue
                objetos_antes = tipos.OBJETOS.copy()        # cada paso usa los objetos de valor de su contexto
                ctx_rv = rv.ctx
                tipos.usar_objetos({v["nombre"]: {c["nombre"]: c for c in v["campos"]}
                                    for a in ctx_rv["agregados"] for v in a["objetos_valor"] + a["entidades"]})
                con = op.get("con") or {}
                if not isinstance(con, dict):
                    self.error(f"{dp} > con", "es un mapa {dato: valor}")
                    con = {}
                for k, v in con.items():
                    if k not in campos:
                        self.error(f"{dp} > con", f'"{k}" no está en la entrada (o en los datos) de "{nombre}"')
                    elif not valor_valido(v, campos[k]):
                        self.error(f"{dp} > con", f'el valor {v!r} no es válido para "{k}" ({campos[k]["tipo"]})')
                if "espera" in op:
                    self.revisar_espera(op["espera"], tipo, nombre, rv, dp, eventos, envios, codigos)
                tipos.usar_objetos(objetos_antes)

    def revisar_espera(self, esp, tipo, nombre, rv, dp, eventos, envios, codigos):
        de = f"{dp} > espera"
        if isinstance(esp, bool):
            self.error(de, "espera no puede ser true o false")
        elif isinstance(esp, int):
            if esp not in codigos[tipo]:
                self.error(de, f"el código {esp} no se permite en un {tipo}; se permiten {sorted(codigos[tipo])}")
        elif isinstance(esp, (str, list)):
            if tipo == "consulta":
                self.error(de, "una consulta no publica eventos; usa espera: {dato: valor} o un código")
            for x in [esp] if isinstance(esp, str) else esp:
                if x not in eventos and x not in envios:
                    self.error(de, f'"{x}" no es un evento de un contexto generado ni un mensaje que envíe un SA')
        elif isinstance(esp, dict) and "código" in esp:
            cod = esp.get("código")
            if not isinstance(cod, int) or isinstance(cod, bool) or cod not in codigos[tipo]:
                self.error(de, f"el código {cod!r} no se permite en un {tipo}; se permiten {sorted(codigos[tipo])}")
            for k, v in esp.items():
                if k != "código" and (k not in CAMPOS_DE_ERROR or not isinstance(v, str)):
                    self.error(f"{de} > {k}", f'se afirma un campo de la respuesta de error ({", ".join(CAMPOS_DE_ERROR)}) con un texto')
        elif isinstance(esp, dict):
            if tipo != "consulta":
                self.error(de, "espera: {dato: valor, ...} solo va en una consulta")
                return
            qy = rv.qs_y[nombre] or {}
            salida_q = {}
            for k, v in {**(qy.get("salida") or {}), **(qy.get("calculados") or {})}.items():
                try:
                    salida_q[k] = tipos.interpretar(v)
                except tipos.TipoInvalido:
                    pass
            if isinstance(qy.get("lista"), str):
                salida_q = {qy["lista"]: tipos.interpretar("int")}
            for k, v in esp.items():
                if k not in salida_q:
                    self.error(de, f'"{k}" no está en la salida de "{nombre}"')
                elif salida_q[k]["lista"] and isinstance(v, int) and not isinstance(v, bool):
                    pass
                elif not valor_valido(v, salida_q[k]):
                    self.error(de, f'el valor {v!r} no es válido para "{k}" ({salida_q[k]["tipo"]})')
        else:
            self.error(de, "espera es un evento, una lista de eventos, un código HTTP o {dato de la salida: valor, ...}")


def revisores_de_contextos(modelo: dict, rutas: list[str]) -> tuple[dict[str, Revisor], list[str]]:
    """Revisa los YAML de contextos de la lista y devuelve sus revisores por contexto, y los errores."""
    revisores, errores = {}, []
    for ruta in rutas:
        spec = cargar_yaml(ruta)
        if es_entre_contextos(spec):
            continue
        rv = Revisor(modelo, spec, ruta)
        rv.revisar()
        if rv.errores:
            errores.append(f"{ruta} tiene errores: revísalo primero")
        elif isinstance(spec, dict):
            revisores[spec.get("contexto")] = rv
    return revisores, errores
