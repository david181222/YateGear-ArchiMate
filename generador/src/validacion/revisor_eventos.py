"""Revisión de los eventos del contexto, las políticas internas y los eventos de otros contextos."""
from __future__ import annotations

from comun import tipos
from validacion.valores import disparos, mismo_tipo, OPCIONES_DISPARO, valor_valido


class RevisionDeEventos:
    """Revisa las secciones eventos, politicas y eventos_de_otros_contextos del YAML."""

    def revisar_eventos(self):
        s, evs_m, bolsas_evento = self.s, self.evs_m, self.bolsas_evento
        evs_y = self.mapa(s.get("eventos"), "eventos")
        self.cubre("eventos", evs_y, evs_m, "evento")
        datos_evento = self.datos_evento = {}
        for n in sorted(set(evs_y) & set(evs_m)):
            d = f"eventos > {n}"
            rc = self.raiz_por_agregado.get(evs_m[n]["agregado_id"])
            if rc:                                        # el evento lleva la identidad de la raíz de su agregado
                self.usar(rc)
            e = self.mapa(evs_y[n], d, ["datos", "calculados"], ["datos"])
            datos = self.campos(e.get("datos"), f"{d} > datos")
            calc = self.campos(e.get("calculados"), f"{d} > calculados")
            datos_evento[n] = {**datos, **calc}
            for cmd, bolsa, propios, nraiz in bolsas_evento.get(n, []):
                self.usar(self.raices[nraiz])
                self.pide(bolsa, datos, f"{d} > datos", f'el evento (publicado por "{cmd}")', propios)
                for k in calc:
                    if k in bolsa:
                        self.error(f"{d} > calculados", f'"{k}" ya está disponible en "{cmd}": va en datos')

    def llegan_con(self, ev):
        """Los datos de un evento del contexto, con su identidad, y la raíz de su agregado."""
        ev_m = next((e for e in self.ctx["eventos"] if e["nombre"] == ev), None)
        r_ev = self.raiz_por_agregado.get(ev_m["agregado_id"]) if ev_m else None
        return {**self.datos_evento.get(ev, {}), **({r_ev["id_nombre"]: tipos.interpretar("string")} if r_ev else {})}, r_ev

    def revisar_politicas(self):
        """Políticas internas: el evento debe traer lo que pide la entrada del comando que dispara."""
        s, ctx, ev_por_id, entradas_cmd = self.s, self.ctx, self.ev_por_id, self.entradas_cmd
        datos_evento, llegan_con = self.datos_evento, self.llegan_con
        # Sin entrada en la sección politicas, cada evento dispara el comando por su cuenta. Con entrada (G10, D7):
        # si/salvo (solo si se cumple), con y correspondencias; y para varios disparos, junto_con (deben llegar todos)
        # y uno_de (y además uno de estos, cada uno con su con).
        cmd_por_id = {c["id"]: c["nombre"] for c in ctx["comandos"]}
        evs_de: dict[str, list[str]] = {}
        for p in ctx["politicas"]:
            evs_de.setdefault(cmd_por_id.get(p["comando_id"]), []).append(ev_por_id.get(p["evento_id"]))
        pol_y = self.mapa(s.get("politicas"), "politicas")
        for cmd in sorted(set(pol_y) - set(evs_de)):
            self.error(f"politicas > {cmd}", "en el modelo ningún evento del contexto dispara este comando")

        for cmd, evs in sorted(evs_de.items()):
            if cmd not in entradas_cmd or any(ev not in datos_evento for ev in evs):
                continue
            d = f"politicas > {cmd}"
            x = self.mapa(pol_y.get(cmd), d, ["junto_con", "uno_de", "si", "salvo", "con", "correspondencias"])
            r_cmd = self.raices.get(entradas_cmd[cmd]["raiz"])
            crea, ent = entradas_cmd[cmd]["crea"], entradas_cmd[cmd]["entrada"]
            for ev in evs:
                _, r_ev = llegan_con(ev)
                if r_ev and r_cmd and not crea and r_ev["id_nombre"] != r_cmd["id_nombre"]:
                    self.error(f'política "{ev}" dispara "{cmd}"', f'el evento lleva "{r_ev["id_nombre"]}" y "{cmd}" necesita '
                               f'"{r_cmd["id_nombre"]}": una política entre raíces con distinta identidad todavía no se genera')
            junto = [e for e in self.lista(x.get("junto_con"), f"{d} > junto_con") if isinstance(e, str)]
            uno_y = x.get("uno_de")
            uno = {k: (v or {}) for k, v in uno_y.items()} if isinstance(uno_y, dict) else \
                {k: {} for k in self.lista(uno_y, f"{d} > uno_de") if isinstance(k, str)}
            if not (junto or uno):                        # un disparo por evento, con las opciones de la entrada
                for ev in evs:
                    llegan, _ = llegan_con(ev)
                    self.revisar_disparo(cmd, x, llegan, llegan, entradas_cmd,
                                         d if cmd in pol_y else f'política "{ev}" dispara "{cmd}"', f'"{ev}"')
                continue
            # Varios disparos (D7): el comando corre cuando llegaron todos los de junto_con y uno de los de uno_de, para la
            # misma identidad. Sus datos salen de los eventos que llegaron, por su nombre.
            if sorted(set(junto) | set(uno)) != sorted(evs) or set(junto) & set(uno):
                self.error(d, f'junto_con y uno_de nombran, sin repetir, los eventos que disparan "{cmd}" en el modelo: '
                              + ", ".join(sorted(evs)))
                continue
            for k in ("si", "salvo"):
                if k in x:
                    self.error(f"{d} > {k}", "si y salvo van en una política de un solo disparo")
            con = self.mapa(x.get("con"), f"{d} > con")
            for k, v in con.items():
                if k not in ent:
                    self.error(f"{d} > con", f'"{k}" no está en la entrada de "{cmd}"')
                elif not valor_valido(v, ent[k]):
                    self.error(f"{d} > con", f'el valor {v!r} no es válido para "{k}" ({ent[k]["tipo"]})')
            corr = self.mapa(x.get("correspondencias"), f"{d} > correspondencias")
            seguros = {}
            for ev in junto:
                seguros.update(llegan_con(ev)[0])
            por_uno = {}
            for ev, o in uno.items():
                o = self.mapa(o, f"{d} > uno_de > {ev}", ["con"])
                llegan = dict(llegan_con(ev)[0])
                for k, v in self.mapa(o.get("con"), f"{d} > uno_de > {ev} > con").items():
                    if k not in ent:
                        self.error(f"{d} > uno_de > {ev} > con", f'"{k}" no está en la entrada de "{cmd}"')
                    elif not valor_valido(v, ent[k]):
                        self.error(f"{d} > uno_de > {ev} > con", f'el valor {v!r} no es válido para "{k}" ({ent[k]["tipo"]})')
                    else:
                        llegan[k] = ent[k]
                por_uno[ev] = llegan
            for k, tk in ent.items():
                fuente_k = corr.get(k, k)
                if k in con:
                    continue
                if k in corr and not isinstance(fuente_k, str):
                    self.error(f"{d} > correspondencias", f'"{k}" se toma de un dato: escribe su nombre')
                    continue
                if fuente_k in seguros:
                    t_llega = seguros[fuente_k]
                elif por_uno and all(fuente_k in ll or k in ll for ll in por_uno.values()):
                    t_llega = next(ll.get(fuente_k) or ll[k] for ll in por_uno.values())
                elif any(fuente_k in ll or k in ll for ll in por_uno.values()):
                    if not tk["opcional"]:
                        self.error(d, f'"{cmd}" necesita "{k}" y solo lo traen algunos de uno_de: debe ser opcional')
                    continue
                else:
                    if not tk["opcional"]:
                        self.error(d, f'"{cmd}" necesita "{k}" y ningún evento lo trae (ni con ni correspondencias)')
                    continue
                if not mismo_tipo(t_llega, tk):
                    self.error(d, f'"{fuente_k}" llega como {t_llega["tipo"]} y "{cmd}" espera "{k}" como {tk["tipo"]}')

    def revisar_eventos_externos(self):
        s, ctx, evs_m, entradas_cmd = self.s, self.ctx, self.evs_m, self.entradas_cmd
        catalogo = {}
        for o in ctx["otros_contextos"]:
            for e in o["eventos"]:
                catalogo.setdefault(e["nombre"], []).append(o["nombre"])
        ext = self.ext_y = self.mapa(s.get("eventos_de_otros_contextos"), "eventos_de_otros_contextos")
        self.identidad_externos: dict[str, str] = {}      # evento de otro contexto -> dato con que llega
        for n in sorted(ext):
            d = f"eventos_de_otros_contextos > {n}"
            x = self.mapa(ext[n], d, ["de", "identidad", "dispara", "con", "correspondencias", "junto_con", "datos"], ["de", "datos"])
            if n in evs_m:
                self.error(d, "es un evento de este contexto, no de otro")
            elif n not in catalogo:
                self.error(d, f'"{n}" no existe en el modelo como evento de otro contexto')
            elif x.get("de") not in catalogo[n]:
                self.error(d, f'en el modelo "{n}" es de {", ".join(catalogo[n])}, no de "{x.get("de")}"')
            # La raíz del evento: la del (primer) comando que dispara; si no dispara y hay varias raíces, su identidad
            # se escribe. dispara puede ser un comando o varios, cada uno con sus opciones (en orden; si uno falla, los
            # siguientes no corren).
            lista = disparos(x) if "dispara" in x else []
            if "dispara" in x and not lista:
                self.error(f"{d} > dispara", "es un comando, una lista de comandos o {comando: {con, correspondencias, si, salvo}}")
            varios = "dispara" in x and not isinstance(x.get("dispara"), str)
            for k in ("con", "correspondencias", "junto_con"):
                if varios and k in x:
                    self.error(f"{d} > {k}", f"con varios comandos en dispara, {k} va en cada comando (junto_con, solo con uno)")
            cmd_d = lista[0][0] if lista else None
            if cmd_d in entradas_cmd:
                self.usar(self.raices[entradas_cmd[cmd_d]["raiz"]])
            elif "identidad" not in x and len(self.raices) > 1:
                self.error(f"{d} > identidad", "el contexto tiene varias raíces: di con qué dato llega el evento (identidad)")
            # identidad: el dato con que llega el evento (por defecto, la identidad de la raíz de este contexto).
            id_ev = x.get("identidad", self.id_nombre)
            self.identidad_externos[n] = id_ev            # para los contratos entre contextos (revisar_contratos)
            if not isinstance(id_ev, str) or not id_ev.strip():
                self.error(f"{d} > identidad", "es el nombre del dato con que llega el evento")
            elif id_ev in (x.get("datos") or {}):
                self.error(f"{d} > datos", f'"{id_ev}" es la identidad del evento: se agrega sola')
            if "dispara" not in x:
                # Sin dispara, el evento solo se recuerda, para los comandos que lo requieren (requiere). Puede llevar
                # correspondencias {dato del comando: dato del evento}, para un dato que llega con otro nombre (D2).
                for k in ("con", "junto_con"):
                    if k in x:
                        self.error(d, f"{k} solo va con dispara")
                if n not in self.requeridos:
                    self.error(d, "no dispara ningún comando y ningún comando lo requiere (requiere): nadie lo usa")
                datos_ev = self.campos(x.get("datos"), f"{d} > datos")
                for local, del_ev in self.mapa(x.get("correspondencias"), f"{d} > correspondencias").items():
                    if not isinstance(del_ev, str) or del_ev not in datos_ev:
                        self.error(f"{d} > correspondencias", f'"{local}" se toma de "{del_ev}", que no está en los datos del evento')
                    elif local in datos_ev:
                        self.error(f"{d} > correspondencias", f'"{local}" ya es un dato del evento: no necesita correspondencia')
                continue
            # La identidad de la raíz de cada comando: la del evento o (G3) un dato del evento con su nombre.
            ids_raiz = {self.raices[entradas_cmd[c_]["raiz"]]["id_nombre"] for c_, _ in lista if c_ in entradas_cmd}
            datos_ev = self.campos(x.get("datos"), f"{d} > datos", permitidos=tuple(ids_raiz - {id_ev}))
            junto = {}                                    # datos de los eventos de junto_con
            for otro in self.lista(x.get("junto_con"), f"{d} > junto_con"):
                o = ext.get(otro) if isinstance(ext.get(otro), dict) else None
                if o is None:
                    self.error(f"{d} > junto_con", f'"{otro}" no está en esta sección')
                    continue
                if o.get("dispara") != cmd_d or n not in (o.get("junto_con") or []):
                    self.error(f"{d} > junto_con", f'"{otro}" debe disparar "{cmd_d}" y nombrar a "{n}" en su junto_con')
                for k, t in (o.get("datos") or {}).items():
                    try:
                        junto.setdefault(k, tipos.interpretar(t))
                    except tipos.TipoInvalido:
                        pass
            # Con junto_con, el comando corre con el último que llega: las correspondencias valen para todo el grupo.
            corr_grupo = {}
            for otro in self.lista(x.get("junto_con"), f"{d} > junto_con"):
                if isinstance(ext.get(otro), dict) and isinstance(ext[otro].get("correspondencias"), dict):
                    corr_grupo.update(ext[otro]["correspondencias"])
            if corr_grupo and lista:
                lista = [(lista[0][0], {**lista[0][1], "correspondencias": {**corr_grupo, **(lista[0][1].get("correspondencias") or {})}})]
            usados = set()
            for cmd, op in lista:
                dd = f"{d} > dispara > {cmd}" if varios else d
                if cmd not in entradas_cmd:
                    self.error(d, f'dispara "{cmd}", que no es un comando especificado del contexto')
                    continue
                if entradas_cmd[cmd]["crea"]:
                    self.error(dd, f'"{cmd}" crea la raíz: un evento de otro contexto no puede dispararlo')
                    continue
                self.usar(self.raices[entradas_cmd[cmd]["raiz"]])
                otra_identidad = id_ev != self.id_nombre  # G3: la identidad de la raíz sale de los datos, por su nombre
                if otra_identidad and self.id_nombre not in datos_ev:
                    self.error(f"{d} > datos", f'llega con "{id_ev}" y dispara "{cmd}": debe traer "{self.id_nombre}", la identidad de la raíz')
                aporta = dict(datos_ev)
                if otra_identidad:                        # la identidad del evento también le sirve al comando
                    aporta.pop(self.id_nombre, None)
                    aporta.setdefault(id_ev, tipos.interpretar("string"))
                for k, t in junto.items():
                    aporta.setdefault(k, t)
                llegan = {**aporta, **datos_ev}
                usados |= self.revisar_disparo(cmd, op, aporta, llegan, entradas_cmd, dd, "el evento (ni junto_con)")
            for k in sorted((set(datos_ev) | set(junto)) - usados - ids_raiz):
                self.aviso(d, f'"{k}" no está en la entrada de ningún comando que dispara: no se usa')

    def revisar_disparo(self, cmd: str, op: dict, aporta: dict, llegan: dict, entradas_cmd: dict, d: str, quien: str) -> set:
        """Un comando que dispara un evento de otro contexto o un mensaje de un SA. aporta: los datos que le llegan por
        su nombre; llegan: todos los que trae (para las correspondencias y las condiciones). con fija valores de su
        entrada, correspondencias {dato de la entrada: dato que llega} toma un dato que llega con otro nombre (D2),
        si o salvo lo dispara solo si se cumple la condición, y si_existe: true solo si su raíz existe (si no existe,
        el evento no le aplica: no es un error). Devuelve los datos que llegan y el comando usa."""
        op = self.mapa(op, d, list(OPCIONES_DISPARO))
        ent = entradas_cmd[cmd]["entrada"]
        aporta = dict(aporta)
        usados = {k for k in aporta if k in ent}
        for k, v in self.mapa(op.get("con"), f"{d} > con").items():
            if k not in ent:
                self.error(f"{d} > con", f'"{k}" no está en la entrada de "{cmd}"')
            elif not valor_valido(v, ent[k]):
                self.error(f"{d} > con", f'el valor {v!r} no es válido para "{k}" ({ent[k]["tipo"]})')
            else:
                aporta[k] = ent[k]
        for k, dato in self.mapa(op.get("correspondencias"), f"{d} > correspondencias").items():
            if k not in ent:
                self.error(f"{d} > correspondencias", f'"{k}" no está en la entrada de "{cmd}"')
            elif not isinstance(dato, str) or dato not in llegan:
                self.error(f"{d} > correspondencias", f'"{k}" se toma de "{dato}", que no llega con {quien}')
            elif not mismo_tipo(llegan[dato], ent[k]):
                self.error(f"{d} > correspondencias", f'"{dato}" llega como {llegan[dato]["tipo"]} y "{cmd}" espera "{k}" como {ent[k]["tipo"]}')
            else:
                aporta[k] = llegan[dato]
                usados.add(dato)
        self.si_salvo(op, llegan, d, frozenset(llegan))
        if "si_existe" in op:
            if op["si_existe"] not in (True, False):
                self.error(f"{d} > si_existe", "es true o false")
            elif op["si_existe"] and entradas_cmd[cmd]["crea"]:
                self.error(f"{d} > si_existe", f'"{cmd}" crea la raíz: no hay una raíz que pueda faltar')
        for k in ("si", "salvo"):
            usados |= set(op.get(k) or {}) if isinstance(op.get(k), dict) else set()
        for k, tk in aporta.items():
            if k in ent and not mismo_tipo(ent[k], tk):
                self.error(d, f'"{k}" llega como {tk["tipo"]} y "{cmd}" lo espera como {ent[k]["tipo"]}')
        for k, tk in ent.items():
            if not tk["opcional"] and k not in aporta:
                self.error(d, f'"{cmd}" necesita "{k}" y {quien} no lo trae (ni con ni correspondencias)')
        return usados
