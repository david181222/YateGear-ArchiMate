"""Escenarios de prueba: la llamada HTTP de cada paso, su identidad y lo que se espera."""
from __future__ import annotations

import json

from comun import nombres, tipos
from generacion.csharp import ejemplo, ErrorDeGeneracion, valor_json
from validacion import valores


def es_rechazo(esp) -> bool:
    """Un paso espera un rechazo si espera un código HTTP, solo o con su motivo."""
    return isinstance(esp, int) or (isinstance(esp, dict) and "código" in esp)


def espera_sin_datos(esp) -> dict | None:
    """Lo esperado de un paso cuando no depende de lo que el paso devuelve: nada (2xx), un código o un rechazo con
    su motivo (campos de la respuesta de error). None si espera eventos o datos de una consulta."""
    if esp is None:
        return {"tipo": "exito", "texto": "HTTP 2xx"}
    if isinstance(esp, int):
        return {"tipo": "codigo", "valor": esp, "texto": f"HTTP {esp}"}
    if isinstance(esp, dict) and "código" in esp:
        campos = {valores.CAMPOS_DE_ERROR[k]: (nombres.pascal(v) if k == "estado actual" else v)
                  for k, v in esp.items() if k != "código"}
        return {"tipo": "codigo", "valor": esp["código"], "campos": campos,
                "texto": f'HTTP {esp["código"]} y ' + ", ".join(f"{k} = {v}" for k, v in esp.items() if k != "código")}
    return None


def espera_de_salida(esp: dict, consulta: dict) -> dict:
    """Lo esperado de una consulta: {dato de la salida: valor, ...}; en una lista, cuántos elementos tiene."""
    tipos_salida = {s["nombre"]: s["tipo"] for s in consulta["salida_campos"]}
    return {"tipo": "salida", "valores": {nombres.camel(k): valor_json(v, tipos_salida[k]) for k, v in esp.items()},
            "texto": "HTTP 2xx y " + ", ".join(f"{k} = {v}" for k, v in esp.items())}


class Escenarios:
    """Prepara los escenarios del contexto y sus pruebas.http."""

    # ------------------------------------------------------------ escenarios
    def preparar_escenarios(self) -> list[dict]:
        """Cada escenario del YAML, con la llamada HTTP de cada paso, su identidad y lo esperado (de "espera").

        Cada paso trabaja con la raíz de su comando, consulta o evento (G2). Su identidad: un comando que crea la
        raíz la recibe (el siguiente consecutivo de esa raíz, que una solicitud rechazada no gasta, o la que se
        forma con sus datos); los demás pasos la toman de con, o si no, de la última identidad con el mismo nombre
        de dato en el escenario (regla de los datos: el calendario de un yate tiene la identidad del yate). Un
        evento de otro contexto con su propia identidad la toma de con.
        """
        cmd = {c["nombre"]: c for c in self.comandos}
        qs = {q["nombre"]: q for q in self.consultas}
        ext = {x["nombre"]: x for x in self.externos}
        msjs = {m["nombre"]: m for m in self.mensajes}
        escenarios, contador = [], {}
        # Coherencia (H-J5-02): las raíces que crean los pasos anteriores, en el orden en que corren (los escenarios
        # comparten la aplicación). Solo avisa: a veces repetir una identidad o usar una raíz inexistente es a propósito.
        creadas: dict[tuple, str] = {}
        self.avisos_escenarios = []
        for nombre_e, pasos in self.s["escenarios"].items():
            actual, primera, lista = {}, None, []
            for i, paso in enumerate(pasos, 1):
                nombre, op = (paso, {}) if isinstance(paso, str) else next(iter(paso.items()))
                op = op or {}
                con = op.get("con") or {}
                esp = op.get("espera")
                rechazo = es_rechazo(esp)

                def cuerpo(campos, identidad=None, nombre_id=None):
                    b = {nombre_id: identidad} if identidad is not None else {}
                    for c in campos:
                        v = con[c["nombre"]] if c["nombre"] in con else None
                        b[nombres.camel(c["nombre"])] = valor_json(v, c["tipo"]) if c["nombre"] in con else ejemplo(c["nombre"], c["tipo"])
                    return b

                if nombre in cmd:
                    raiz_paso = cmd[nombre]["raiz_nombre"]
                elif nombre in msjs:
                    raiz_paso = cmd[msjs[nombre]["comando"]]["raiz_nombre"]
                elif nombre in qs:
                    raiz_paso = qs[nombre]["raiz_nombre"]
                else:
                    raiz_paso = cmd[ext[nombre]["comando"]]["raiz_nombre"] if ext[nombre]["comando"] else None
                r = self.usar_raiz(raiz_paso) if raiz_paso else None
                id_json = nombres.camel(r["id_nombre"]) if r else None
                previa = (con.get(r["id_nombre"]) or actual.get(r["id_nombre"])) if r else None
                ident = previa

                def identidad_al_crear(c, datos):
                    """La identidad que recibe la raíz que crea el comando c con este cuerpo (None si es un rechazo)."""
                    if r["consecutivo"]:
                        n_sig = contador.get(raiz_paso, 0) + 1
                        contador[raiz_paso] = n_sig - (1 if rechazo else 0)
                        return None if rechazo else r["prefijo"] + str(n_sig).zfill(r["digitos"])
                    valores = {**{k: valor_json(v, self.tipos_raiz[k]) for k, v in (c["spec"].get("valores") or {}).items()},
                               **{e["nombre"]: datos.get(nombres.camel(e["nombre"])) for e in c["entrada_campos"]}}
                    for g in c["spec"].get("guarda") or []:     # {campo: dato}: el campo vale lo que el dato
                        if isinstance(g, dict) and isinstance(next(iter(g.values())), str):
                            campo, dato = next(iter(g.items()))
                            if dato in valores:
                                valores.setdefault(campo, valores[dato])
                    faltan = [parte for parte in r["id_de"] if parte not in valores]
                    if faltan:
                        raise ErrorDeGeneracion(
                            f'escenario "{nombre_e}", paso {i}: la identidad que forma "{c["nombre"]}" usa '
                            f'{", ".join(chr(34) + x + chr(34) for x in faltan)}, que no sale de su entrada ni de sus valores '
                            f'(sale de un evento o de un servicio SA); los escenarios solo calculan la identidad con esos dos')
                    return "/".join(str(valores[parte]) for parte in r["id_de"])

                if nombre in msjs:                      # un mensaje de un SA (G7): como el comando que dispara
                    msj = msjs[nombre]
                    c = cmd[msj["comando"]]
                    tipo, metodo, crea = "mensaje de un servicio SA", "POST", c["crea"]
                    ruta = msj["ruta"].removeprefix(self.ruta_base)
                    datos = cuerpo(msj["datos_campos"])
                    if crea:
                        ident = identidad_al_crear(c, datos)
                        if not rechazo:
                            primera = primera or ident
                    else:
                        if r["id_nombre"] not in con and previa:
                            datos[id_json] = previa
                        ident = datos.get(id_json)
                elif nombre in cmd and cmd[nombre]["todas"]:   # sobre todas las raíces (G8): sin identidad
                    c = cmd[nombre]
                    tipo, metodo, crea = "comando", "POST", False
                    ruta, datos, ident = c["ruta"].removeprefix(self.ruta_base), cuerpo(c["entrada_campos"]), None
                elif nombre in cmd:
                    c = cmd[nombre]
                    tipo, metodo, ruta = "comando", "POST", c["ruta"].removeprefix(self.ruta_base)
                    crea = c["crea"]
                    if crea:
                        datos = cuerpo(c["entrada_campos"])
                        ident = identidad_al_crear(c, datos)
                        if not rechazo:
                            primera = primera or ident
                    else:
                        datos = cuerpo(c["entrada_campos"], ident, id_json)
                elif nombre in qs:
                    q = qs[nombre]
                    tipo, metodo, crea, datos = "consulta", "GET", False, None
                    ruta = q["ruta_prueba"] if q["todas"] else f'{q["ruta_prueba"]}/{ident}'
                    if q["todas"]:
                        ident = None
                    extra = cuerpo(q["entrada_campos"])
                    if extra:
                        ruta += "?" + "&".join(f"{a}={b}" for a, b in extra.items())
                else:
                    x = ext[nombre]
                    tipo, metodo, crea = "evento de otro contexto", "POST", False
                    ruta = x["ruta"].removeprefix(self.ruta_base)
                    if r and x["id_nombre"] == r["id_nombre"]:
                        datos = cuerpo(x["datos_campos"], ident, id_json)
                    else:                               # el evento llega con su propia identidad: sale de con
                        id_ev = con.get(x["id_nombre"], ejemplo(x["id_nombre"], tipos.interpretar("string")))
                        datos = cuerpo(x["datos_campos"], id_ev, nombres.camel(x["id_nombre"]))
                        if r:                           # la identidad de la raíz va en sus datos (G3)
                            if r["id_nombre"] not in con and previa:
                                datos[id_json] = previa
                            ident = datos.get(id_json)
                        else:
                            ident = None
                if r and ident:
                    clave, donde = (raiz_paso, ident), f'escenario "{nombre_e}", paso {i} ("{nombre}")'
                    espera_codigo = esp if isinstance(esp, int) else (esp.get("código") if isinstance(esp, dict) else None)
                    cmd_paso = cmd.get(nombre) or (cmd[msjs[nombre]["comando"]] if nombre in msjs else None)
                    crea_aqui = (cmd_paso is not None and (cmd_paso["crea"] or cmd_paso["si_no_existe"])) or \
                                (nombre in ext and ext[nombre]["comando"] and cmd[ext[nombre]["comando"]]["si_no_existe"])
                    # Un evento cuyos comandos llevan todos si_existe no le aplica a una raíz que no existe: responde 2xx.
                    se_paso = (self.s.get("eventos_de_otros_contextos") or {}).get(nombre)
                    no_aplica = isinstance(se_paso, dict) and "dispara" in se_paso and \
                        all(op.get("si_existe") for _, op in valores.disparos(se_paso))
                    if cmd_paso is not None and cmd_paso["crea"]:
                        if clave in creadas and espera_codigo != 409:
                            self.avisos_escenarios.append(f'{donde}: crea "{ident}", que ya creó {creadas[clave]}; '
                                                          "si se espera el rechazo, escribe espera: 409")
                    elif not crea_aqui and clave not in creadas and espera_codigo != 404 and not no_aplica:
                        self.avisos_escenarios.append(f'{donde}: usa "{ident}" ({raiz_paso}), que ningún paso anterior creó; '
                                                      "si se espera que no exista, escribe espera: 404")
                    if not rechazo:
                        creadas.setdefault(clave, donde)
                        if nombre in msjs:                # un mensaje que dispara varios comandos crea las raíces de todos
                            for otro in msjs[nombre]["comandos"][1:]:
                                if cmd[otro]["crea"]:
                                    creadas.setdefault((cmd[otro]["raiz_nombre"], ident), donde)
                if r and ident and not rechazo:
                    actual[r["id_nombre"]] = ident
                espera = espera_sin_datos(esp)
                if espera is None and isinstance(esp, str):
                    espera = {"tipo": "evento", "valor": esp, "texto": f'HTTP 2xx y el evento "{esp}"'}
                elif espera is None:
                    espera = espera_de_salida(esp, qs[nombre])
                lista.append({"numero": i, "nombre": nombre, "tipo": tipo, "crea": crea, "identidad": ident,
                              "metodo": metodo, "ruta": ruta, "cuerpo": datos, "espera": espera})
            escenarios.append({"nombre": nombre_e, "identidad": primera or "", "pasos": lista})
        return escenarios

    def paso_entre_contextos(self, nombre: str, con: dict, actual: dict, contador: dict, rechazo: bool) -> dict:
        """Un paso de un escenario entre contextos (S4) en este contexto: la llamada HTTP (con la ruta completa), su
        cuerpo y su identidad. Un dato de la entrada que no está en con y se llama como una identidad ya creada en el
        escenario (actual) toma su valor; los demás, un valor de ejemplo."""
        cmd = {c["nombre"]: c for c in self.comandos}
        qs = {q["nombre"]: q for q in self.consultas}
        msjs = {m["nombre"]: m for m in self.mensajes}

        def valor(c):
            if c["nombre"] in con:
                return valor_json(con[c["nombre"]], c["tipo"])
            if c["nombre"] in actual and c["tipo"]["base"] == "string" and not c["tipo"]["lista"]:
                return actual[c["nombre"]]
            return ejemplo(c["nombre"], c["tipo"])

        def cuerpo(campos):
            return {nombres.camel(c["nombre"]): valor(c) for c in campos}

        def creada(c, r, datos):
            """La identidad que recibe la raíz que crea el comando c (None si el paso es un rechazo a propósito)."""
            if rechazo:
                return None
            if r["consecutivo"]:
                clave = (self.proyecto, r["nombre"])
                contador[clave] = contador.get(clave, 0) + 1
                return r["prefijo"] + str(contador[clave]).zfill(r["digitos"])
            valores = {k: valor_json(v, self.tipos_raiz[k]) for k, v in (c["spec"].get("valores") or {}).items()}
            valores.update({e["nombre"]: datos.get(nombres.camel(e["nombre"])) for e in c["entrada_campos"]})
            faltan = [x for x in r["id_de"] if x not in valores]
            if faltan:
                raise ErrorDeGeneracion(f'"{nombre}": la identidad que forma "{c["nombre"]}" usa {", ".join(faltan)}, '
                                        "que no sale de su entrada ni de sus valores")
            return "/".join(str(valores[x]) for x in r["id_de"])

        if nombre in msjs:                              # un mensaje de un SA (G7), como el comando que dispara
            m = msjs[nombre]
            c = cmd[m["comando"]]
            r = self.usar_raiz(c["raiz_nombre"])
            datos = cuerpo(m["datos_campos"])
            ident = creada(c, r, datos) if c["crea"] else datos.get(nombres.camel(r["id_nombre"]))
            return {"tipo": "mensaje de un servicio SA", "metodo": "POST", "ruta": m["ruta"], "cuerpo": datos,
                    "identidad": ident, "crea": c["crea"], "id_nombre": r["id_nombre"]}
        if nombre in cmd:
            c = cmd[nombre]
            r = self.usar_raiz(c["raiz_nombre"])
            if c["todas"]:
                return {"tipo": "comando", "metodo": "POST", "ruta": c["ruta"], "cuerpo": cuerpo(c["entrada_campos"]),
                        "identidad": None, "crea": False, "id_nombre": r["id_nombre"]}
            if c["crea"]:
                datos = cuerpo(c["entrada_campos"])
                ident = creada(c, r, datos)
            else:
                ident = con.get(r["id_nombre"]) or actual.get(r["id_nombre"])
                datos = {nombres.camel(r["id_nombre"]): ident, **cuerpo(c["entrada_campos"])}
            return {"tipo": "comando", "metodo": "POST", "ruta": c["ruta"], "cuerpo": datos, "identidad": ident,
                    "crea": c["crea"], "id_nombre": r["id_nombre"]}
        q = qs[nombre]
        r = self.usar_raiz(q["raiz_nombre"])
        ident = None if q["todas"] else (con.get(r["id_nombre"]) or actual.get(r["id_nombre"]))
        ruta = self.ruta_base + q["ruta_prueba"] + ("" if q["todas"] else f"/{ident}")
        extra = cuerpo(q["entrada_campos"])
        if extra:
            ruta += "?" + "&".join(f"{a}={b}" for a, b in extra.items())
        return {"tipo": "consulta", "metodo": "GET", "ruta": ruta, "cuerpo": None, "identidad": ident, "crea": False,
                "id_nombre": r["id_nombre"]}

    def pruebas_de_escenarios(self, escenarios: list[dict]) -> list[dict]:
        pruebas = []
        for k, e in enumerate(escenarios, 1):
            for p in e["pasos"]:
                pruebas.append({
                    "encabezado": f'Escenario {k}: {e["nombre"]} ({e["identidad"]})' if p["numero"] == 1 else None,
                    "titulo": f'{e["nombre"]} · paso {p["numero"]}: {p["nombre"]}',
                    "comentarios": [f'{p["tipo"].capitalize()}. Espera: {p["espera"]["texto"]}.'],
                    "metodo": p["metodo"], "ruta": p["ruta"],
                    "cuerpo": json.dumps(p["cuerpo"], ensure_ascii=False, indent=2) if p["cuerpo"] is not None else None})
        return pruebas

    # ------------------------------------------------------------ pruebas.http sin escenarios
    def preparar_pruebas(self) -> list[dict]:
        r = self.raiz
        cuenta = [0]

        def nueva_identidad():
            cuenta[0] += 1
            if not r["consecutivo"]:                    # se forma con los datos del comando que la crea
                return "{" + "/".join(r["id_de"]) + "}"
            return r["prefijo"] + str(cuenta[0]).zfill(r["digitos"])

        def cuerpo(cmd, identidad, cambios=None):
            b = {} if cmd["crea"] else {nombres.camel(r["id_nombre"]): identidad}
            for c in cmd["entrada_campos"]:
                b[nombres.camel(c["nombre"])] = ejemplo(c["nombre"], c["tipo"])
            for k, val in (cambios or {}).items():
                b[nombres.camel(k)] = val
            return json.dumps(b, ensure_ascii=False, indent=2)

        def llamada(cmd, identidad, nota, cambios=None):
            return {"titulo": f'{cmd["codigo"]} {cmd["nombre"]}', "comentarios": [nota], "metodo": "POST",
                    "ruta": cmd["ruta"].removeprefix(self.ruta_base), "cuerpo": cuerpo(cmd, identidad, cambios)}

        # Las llamadas siguen el orden del YAML, que es el orden del flujo; el resto del código va por nombre.
        pruebas = []
        en_yaml = list(self.s["comandos"])
        por_yaml = sorted(self.comandos, key=lambda c: en_yaml.index(c["nombre"]))
        crea = next(c for c in por_yaml if c["crea"])
        orden = [crea] + [c for c in por_yaml if not c["crea"]]
        principal = nueva_identidad()
        for c in orden:
            nota = f"Crea la raíz {principal}." if c["crea"] else f"Sobre {principal}."
            pruebas.append(llamada(c, principal, nota))
        q_yaml = list(self.s["consultas"])
        for q in sorted(self.consultas, key=lambda q: q_yaml.index(q["nombre"])):
            pruebas.append({"titulo": f'{q["codigo"]} {q["nombre"]}', "comentarios": [f"Sobre {principal}."], "metodo": "GET",
                            "ruta": f'{q["ruta_prueba"]}/{principal}', "cuerpo": None})
        bitacora = {"titulo": "Bitácora (infraestructura)", "metodo": "GET", "ruta": "/bitacora", "cuerpo": None,
                    "comentarios": ["Eventos publicados y llamadas a los servicios SA simulados, en orden."]}
        pruebas.append(bitacora)

        # Caminos alternativos: casos de los SA que usa el comando que crea, elegidos por su entrada.
        ent_crea = {c["nombre"] for c in crea["entrada_campos"]}
        con_casos = [c for c in orden if not c["crea"] and any(self.sas[s]["usa_casos"] for s in c["spec"].get("usa") or [])]
        for nombre_sa in crea["spec"].get("usa") or []:
            sa = self.sas[nombre_sa]
            for caso in sa["spec"].get("casos") or []:
                if not set(caso["si"]) <= ent_crea:
                    continue
                ident = nueva_identidad()
                cambios = {k: valor_json(vals[0], next(c["tipo"] for c in crea["entrada_campos"] if c["nombre"] == k))
                           for k, vals in caso["si"].items()}
                texto = ", ".join(f'{k} = {vals[0]}' for k, vals in caso["si"].items())
                pruebas.append(llamada(crea, ident, f'Camino alternativo: caso de "{nombre_sa}" con {texto}. Crea {ident}.', cambios))
                for c in con_casos:
                    pruebas.append(llamada(c, ident, f"Camino alternativo, sobre {ident}."))
                pruebas.append(bitacora)
        return pruebas
