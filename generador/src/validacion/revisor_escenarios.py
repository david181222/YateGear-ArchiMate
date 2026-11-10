"""Revisión de los escenarios de un contexto: solo que estén bien escritos (no se simulan los datos)."""
from __future__ import annotations

from comun import tipos
from validacion.valores import CAMPOS_DE_ERROR, disparos, valor_valido


# Códigos HTTP que un paso puede esperar, según lo que es.
CODIGOS = {"comando": {404, 409, 422}, "consulta": {404, 422}, "evento de otro contexto": {202, 404, 409, 422},
           "mensaje de un servicio SA": {404, 409, 422}}


class RevisionDeEscenarios:
    """Revisa la sección escenarios del YAML."""

    def revisar_escenarios(self):
        s, ctx, entradas_cmd, ext, qs_y, ev_por_id = self.s, self.ctx, self.entradas_cmd, self.ext_y, self.qs_y, self.ev_por_id
        if "escenarios" not in s:
            return
        esc = self.mapa(s.get("escenarios"), "escenarios")
        cmd_por_id = {c["id"]: c["nombre"] for c in ctx["comandos"]}
        eventos_de = {c["nombre"]: {ev_por_id[i] for i in c["eventos"]} for c in ctx["comandos"]}
        politica = {}                                  # evento -> comandos que dispara (políticas internas)
        for p in ctx["politicas"]:
            politica.setdefault(ev_por_id.get(p["evento_id"]), []).append(cmd_por_id.get(p["comando_id"]))

        def alcanzables(cmd, vistos=None):
            """Eventos que publica el comando, directo o por las políticas que disparan sus eventos."""
            vistos = vistos or set()
            if cmd in vistos:
                return set()
            vistos.add(cmd)
            out = set(eventos_de.get(cmd, set()))
            for e in list(out):
                for otro in politica.get(e, []):
                    out |= alcanzables(otro, vistos)
            return out

        llamados = set()
        for nombre_e, pasos in esc.items():
            d = f"escenarios > {nombre_e}"
            pasos = self.lista(pasos, d)
            if not pasos:
                self.error(d, "el escenario no tiene pasos")
            for i, paso in enumerate(pasos, 1):
                dp = f"{d} > paso {i}"
                if isinstance(paso, str):
                    nombre, op = paso, {}
                elif isinstance(paso, dict) and len(paso) == 1:
                    nombre, op = next(iter(paso.items()))
                    op = self.mapa(op, f"{dp} ({nombre})", ["con", "espera"])
                else:
                    self.error(dp, 'un paso es un nombre, o "nombre:" con con y espera')
                    continue
                llamados.add(nombre)
                dp = f"{dp} ({nombre})"
                tipo_y_campos = self.campos_del_paso(nombre, dp)
                if tipo_y_campos is None:
                    continue
                tipo, campos = tipo_y_campos
                for k, v in self.mapa(op.get("con"), f"{dp} > con").items():
                    if k not in campos:
                        self.error(f"{dp} > con", f'"{k}" no está en la entrada (o en los datos) de "{nombre}"')
                    elif not valor_valido(v, campos[k]):
                        self.error(f"{dp} > con", f'el valor {v!r} no es válido para "{k}" ({campos[k]["tipo"]})')
                if "espera" in op:
                    self.revisar_espera(op["espera"], tipo, nombre, dp, alcanzables)
        # Un comando que dispara un evento de otro contexto usado en los escenarios también se prueba.
        llamados |= {c_ for n in list(llamados) if n in ext and isinstance(ext[n], dict) for c_, _ in disparos(ext[n])}
        llamados |= {c_ for n in list(llamados) if n in self.mensajes_sa for c_ in self.mensajes_sa[n]["comandos"]}
        # Y los que disparan las políticas internas de los comandos que se prueban.
        politica_de = {}
        for p in ctx["politicas"]:
            politica_de.setdefault(cmd_por_id.get(p["comando_id"]), set()).add(ev_por_id.get(p["evento_id"]))
        cambia = True
        while cambia:
            alcanzados = set().union(*(alcanzables(c_) for c_ in llamados if c_ in entradas_cmd)) if llamados else set()
            nuevos = {c_ for c_, evs in politica_de.items() if evs & alcanzados} - llamados
            llamados |= nuevos
            cambia = bool(nuevos)
        for n in sorted((set(entradas_cmd) | set(qs_y) | set(ext)) - llamados):
            self.aviso("escenarios", f'"{n}" no aparece en ningún escenario: pruebas.http no lo llamará')

    def campos_del_paso(self, nombre: str, dp: str):
        """Qué es el paso (comando, consulta, mensaje de un SA o evento de otro contexto) y los datos que puede fijar
        con "con". None si el nombre no es nada de eso."""
        ctx, entradas_cmd, ext, qs_y = self.ctx, self.entradas_cmd, self.ext_y, self.qs_y
        if nombre in entradas_cmd:
            tipo, campos = "comando", dict(entradas_cmd[nombre]["entrada"])
            if not entradas_cmd[nombre]["crea"]:  # la identidad de su raíz puede ir en con
                campos.setdefault(self.raices[entradas_cmd[nombre]["raiz"]]["id_nombre"], tipos.interpretar("string"))
        elif nombre in qs_y:
            tipo = "consulta"
            campos = {k: tipos.interpretar(v) for k, v in ((qs_y[nombre] or {}).get("entrada") or {}).items()}
            if (qs_y[nombre] or {}).get("sobre") != "todas":   # por identidad: la de su raíz puede ir en con
                q_m = next((q for q in ctx["consultas"] if q["nombre"] == nombre), None)
                r_q = self.raiz_por_id.get(q_m["lee"][0]["raiz_id"]) if q_m and q_m["lee"] else None
                if r_q:
                    campos.setdefault(r_q["id_nombre"], tipos.interpretar("string"))
        elif nombre in self.mensajes_sa:
            tipo = "mensaje de un servicio SA"
            campos = dict(self.mensajes_sa[nombre]["datos"])
        elif nombre in ext:
            tipo = "evento de otro contexto"
            x = ext[nombre] or {}
            campos = {k: tipos.interpretar(v) for k, v in (x.get("datos") or {}).items()}
            # Su identidad puede ir en con (la toma de con si no es la de la raíz; si lo es, de con o del escenario).
            campos.setdefault(x["identidad"] if isinstance(x.get("identidad"), str) else self.id_nombre,
                              tipos.interpretar("string"))
        else:
            self.error(dp, f'"{nombre}" no es un comando, una consulta, un evento de otro contexto ni un mensaje de un SA del YAML')
            return None
        return tipo, campos

    def revisar_espera(self, esp, tipo: str, nombre: str, dp: str, alcanzables):
        """Lo que espera un paso: un evento que ese paso puede publicar (alcanzables), un código permitido, un rechazo
        con su motivo o, en una consulta, datos de su salida con valores válidos."""
        ext, qs_y = self.ext_y, self.qs_y
        if isinstance(esp, bool):
            self.error(f"{dp} > espera", "espera no puede ser true o false")
        elif isinstance(esp, int):
            if esp not in CODIGOS[tipo]:
                self.error(f"{dp} > espera", f"el código {esp} no se permite en un {tipo}; se permiten {sorted(CODIGOS[tipo])}")
        elif isinstance(esp, str):
            if tipo == "consulta":
                self.error(f"{dp} > espera", "una consulta no publica eventos; usa espera: {estado: ...} o un código")
            else:
                cmds = [nombre] if tipo == "comando" else self.mensajes_sa[nombre]["comandos"] \
                    if tipo == "mensaje de un servicio SA" else [c_ for c_, _ in disparos(ext[nombre] or {})]
                cmd = ", ".join(cmds)
                posibles = set().union(*(alcanzables(c_) for c_ in cmds))
                if esp not in posibles:
                    self.error(f"{dp} > espera", f'"{esp}" no es un evento que publique "{cmd}" (directo o por una política); '
                                                 f'posibles: {", ".join(sorted(posibles))}')
        elif isinstance(esp, dict) and "código" in esp:
            # Un rechazo con su motivo: el código y los campos de la respuesta de error (H-J5-01).
            esp = self.mapa(esp, f"{dp} > espera", ["código"] + list(CAMPOS_DE_ERROR))
            cod = esp.get("código")
            if not isinstance(cod, int) or isinstance(cod, bool) or cod not in CODIGOS[tipo]:
                self.error(f"{dp} > espera", f"el código {cod!r} no se permite en un {tipo}; se permiten {sorted(CODIGOS[tipo])}")
            if len(esp) == 1:
                self.aviso(f"{dp} > espera", "con solo el código, escribe espera: <código>")
            for k, v in esp.items():
                if k != "código" and not isinstance(v, str):
                    self.error(f"{dp} > espera > {k}", "es un texto")
            if "estado actual" in esp:
                self.estados_validos(esp["estado actual"], f"{dp} > espera > estado actual")
        elif isinstance(esp, dict):
            if tipo != "consulta":
                self.error(f"{dp} > espera", "espera: {dato: valor, ...} solo va en una consulta")
            else:
                qy = qs_y[nombre] or {}
                salida_q = {}
                for k, v in {**(qy.get("salida") or {}), **(qy.get("calculados") or {})}.items():
                    try:
                        salida_q[k] = tipos.interpretar(v)
                    except tipos.TipoInvalido:
                        pass
                if isinstance(qy.get("lista"), str):     # una lista se compara por cuántos elementos tiene
                    salida_q = {qy["lista"]: tipos.interpretar("int")}
                if not esp:
                    self.error(f"{dp} > espera", "di qué datos de la salida se esperan")
                for k, v in esp.items():
                    if k not in salida_q:
                        self.error(f"{dp} > espera", f'"{k}" no está en la salida de "{nombre}"')
                    elif k == "estado" and salida_q[k]["base"] == "enum" and salida_q[k]["enum"]["valores"] == self.estados:
                        self.estados_validos(v, f"{dp} > espera > estado")
                    elif salida_q[k]["lista"] and isinstance(v, int) and not isinstance(v, bool):
                        pass                      # una lista se compara por cuántos elementos tiene
                    elif not valor_valido(v, salida_q[k]):
                        self.error(f"{dp} > espera", f'el valor {v!r} no es válido para "{k}" ({salida_q[k]["tipo"]})')
        else:
            self.error(f"{dp} > espera", "espera es un evento, un código HTTP o {dato de la salida: valor, ...}")
