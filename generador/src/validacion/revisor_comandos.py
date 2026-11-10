"""Revisión de los comandos: entrada, datos disponibles, lo que guardan, transiciones y eventos."""
from __future__ import annotations

from comun import tipos
from validacion.valores import COMPARACIONES, ESCRIBEN, mismo_tipo, opcional, OPCIONES_USO_SA, ubicar_calculados, uso_sa, valor_valido


class RevisionDeComandos:
    """Revisa la sección comandos del YAML."""

    def revisar_comandos(self):
        s, ctx = self.s, self.ctx
        cmds_m = {c["nombre"]: c for c in ctx["comandos"]}
        self.evs_m = {e["nombre"]: e for e in ctx["eventos"]}
        self.ev_por_id = {e["id"]: e["nombre"] for e in ctx["eventos"]}
        cmds_y = self.mapa(s.get("comandos"), "comandos")
        self.cubre("comandos", cmds_y, cmds_m, "comando")
        # evento -> (comando que lo publica, datos disponibles, los que no dependen de la raíz, raíz)
        self.bolsas_evento: dict[str, list[tuple]] = {}
        self.entradas_cmd: dict[str, dict] = {}             # comando -> su entrada, si crea, su raíz y si es sobre todas
        # Eventos de otros contextos: los comandos que los requieren (requiere) los necesitan desde ya.
        self.externos_crudos = s.get("eventos_de_otros_contextos") if isinstance(s.get("eventos_de_otros_contextos"), dict) else {}
        self.requeridos: dict[str, list[str]] = {}          # evento de otro contexto -> comandos que lo requieren
        self.crean_por_raiz: dict[str, list[str]] = {}      # raíz -> comandos que la crean
        for n in sorted(set(cmds_y) & set(cmds_m)):
            self.revisar_comando(n, cmds_m[n], cmds_y[n])
        for nr in self.raices:
            if nr not in self.crean_por_raiz:
                self.error("comandos", f'ningún comando crea la raíz "{nr}" (crea: true o crea: si_no_existe)')

    def revisar_comando(self, n: str, m: dict, c_yaml):
        """Un comando: m es el del modelo y c_yaml, el del YAML."""
        entradas_cmd, crean_por_raiz = self.entradas_cmd, self.crean_por_raiz
        d = f"comandos > {n}"
        rc = self.raiz_por_id.get(m["raiz_id"])
        if rc is None:
            return
        con_raiz, todos, campos_raiz, vos, base, estado_t, nombre_raiz = self.usar(rc)
        c = self.mapa(c_yaml, d, ["crea", "desde", "a", "entrada", "valores", "requiere", "usa", "calculados", "guarda",
                                     "eventos", "resultados", "sobre", "temporizador", "reglas"], ["entrada"])
        todas = c.get("sobre") == "todas"             # G8: revisa todas las raíces y publica un evento por cada elegida
        if "sobre" in c and not todas:
            self.error(f"{d} > sobre", 'en un comando solo se permite "sobre: todas"')
        if todas:
            for k in ("crea", "desde", "a", "valores", "requiere", "usa", "guarda", "resultados"):
                if k in c:
                    self.error(d, f"un comando sobre todas las raíces no lleva {k}: solo elige raíces y publica sus eventos")
            if m["acceso"] in ESCRIBEN:
                self.error(d, f"un comando sobre todas las raíces no escribe, y en el modelo su acceso es de {m['acceso']}")
        elif "temporizador" in c:
            self.error(f"{d} > temporizador", "el temporizador va en un comando sobre: todas")
        crea = c.get("crea", False)
        if crea not in (True, False, "si_no_existe"):
            self.error(d, "crea es true, false o si_no_existe")
            crea = False
        si_no_existe = crea == "si_no_existe"         # carga la raíz y, si no existe, la crea vacía
        if si_no_existe:
            crea = False
            if not rc["recibida"]:
                self.error(d, "crea: si_no_existe necesita una identidad recibida (de con un solo dato, la identidad): "
                              "la raíz nueva toma la identidad que trae el comando")
            for campo in campos_raiz.values():
                if not campo["opcional"]:
                    self.error(d, f'crea: si_no_existe crea la raíz vacía, y su campo "{campo["nombre"]}" es obligatorio')
            for v in vos.values():
                if v["cardinalidad"] == "Uno":
                    self.error(d, f'crea: si_no_existe crea la raíz vacía, y "{v["nombre"]}" tiene Cardinalidad Uno')
        if crea or si_no_existe:
            crean_por_raiz.setdefault(nombre_raiz, []).append(n)
            if m["acceso"] not in ESCRIBEN:
                self.error(d, f"el comando crea la raíz pero en el modelo su acceso es de {m['acceso']}")
        # El comando que crea una raíz con identidad recibida la trae en su entrada.
        ent = self.campos(c.get("entrada"), f"{d} > entrada", permitidos=(self.id_nombre,) if crea and rc["recibida"] else ())
        if crea and rc["recibida"] and self.id_nombre not in ent:
            self.error(f"{d} > entrada", f'crea "{nombre_raiz}", cuya identidad es recibida: falta "{self.id_nombre}" en la entrada')
        entradas_cmd[n] = {"entrada": ent, "crea": crea, "raiz": nombre_raiz, "todas": todas}
        if todas and "temporizador" in c:
            self.revisar_temporizador(c["temporizador"], ent, f"{d} > temporizador")
        # El comando que crea la raíz no tiene raíz ni identidad hasta que la guarda (la identidad se
        # asigna al guardar, después de ValidarReglas): sus SA y condiciones solo usan entrada y SA.
        bolsa = {} if crea else dict(con_raiz)
        self.agregar(bolsa, ent, f"{d} > entrada")
        propios = set(ent)
        origenes_cmd = {} if crea else {k: ["raíz"] for k in todos if k in con_raiz}
        for k in ent:
            origenes_cmd.setdefault(k, []).append("entrada")

        # Valores fijos del comando: solo para datos de la raíz, cuyo tipo sale del modelo o de la identidad.
        for k in self.revisar_valores(c.get("valores"), bolsa, f"{d} > valores", todos):
            propios.add(k)
            origenes_cmd.setdefault(k, []).append("valores")

        self.revisar_requiere(n, c, d, bolsa, propios, origenes_cmd)
        self.revisar_calculados_y_sas(n, m, c, d, crea, todas, bolsa, propios, origenes_cmd)
        self.revisar_reglas(c, d, todas, bolsa, propios)
        for k, lista_o in sorted(origenes_cmd.items()):
            if len(lista_o) > 1 and k != self.id_nombre:
                self.varios_origenes.append(f'{n}: "{k}" llega de {", ".join(lista_o)}; se usa {lista_o[-1]}')

        # Lo que guarda en la raíz. Cada dato debe tener un solo destino (regla de los datos).
        guarda = self.lista(c.get("guarda"), f"{d} > guarda")
        if guarda and m["acceso"] not in ESCRIBEN:
            self.error(f"{d} > guarda", f"el comando guarda datos pero en el modelo su acceso a la raíz es de {m['acceso']}")
        guardados = self.revisar_guarda(guarda, bolsa, propios, f"{d} > guarda", campos_raiz, vos, nombre_raiz)
        if crea:
            for v in vos.values():
                if v["cardinalidad"] == "Uno" and v["nombre"] not in guarda:
                    self.error(f"{d} > guarda", f'crea la raíz y no guarda "{v["nombre"]}", que tiene Cardinalidad Uno')
            for campo in campos_raiz.values():
                if not campo["opcional"] and not campo["lista"] and campo["nombre"] not in guardados:
                    self.error(f"{d} > guarda", f'crea la raíz y no guarda su campo obligatorio "{campo["nombre"]}"')
            # Identidad formada con datos: cada parte que no es campo debe estar en la bolsa (los campos ya se guardan).
            for parte in self.id_de or []:
                if parte in self.componentes:
                    self.pide(bolsa, {parte: self.componentes[parte]}, d, "la identidad de la raíz", propios)

        # Transiciones.
        if crea and ("desde" in c or "resultados" in c):
            self.error(d, "el comando que crea la raíz no lleva desde ni resultados")
        if crea and "a" not in c:
            self.error(d, "el comando que crea la raíz debe decir su estado inicial (a)")
        desde = self.estados_validos(c["desde"], f"{d} > desde") if "desde" in c else None
        if "a" in c:
            self.estados_validos(c["a"], f"{d} > a")
        self.revisar_eventos_del_comando(n, m, c, d, crea, todas, bolsa, propios, guardados, desde)

    def revisar_requiere(self, n: str, c: dict, d: str, bolsa: dict, propios: set, origenes_cmd: dict):
        """Eventos de otros contextos que el comando requiere: si no han llegado para su identidad, 409. Sus datos
        entran a la bolsa del comando."""
        ext_y = self.externos_crudos
        for ev in self.lista(c.get("requiere"), f"{d} > requiere"):
            x = ext_y.get(ev)
            if not isinstance(x, dict):
                self.error(f"{d} > requiere", f'"{ev}" no está en eventos_de_otros_contextos')
                continue
            self.requeridos.setdefault(ev, []).append(n)
            id_ev = x.get("identidad", self.id_nombre)
            if id_ev not in bolsa:
                self.error(f"{d} > requiere", f'para buscar "{ev}" hace falta "{id_ev}" (su identidad), y el comando no lo tiene')
            elif bolsa[id_ev]["base"] != "string" or bolsa[id_ev]["lista"]:
                self.error(f"{d} > requiere", f'"{id_ev}", la identidad de "{ev}", debe ser string')
            datos_ev = {}
            for k, tx in (x.get("datos") or {}).items():
                try:
                    datos_ev[k] = tipos.interpretar(tx)
                except tipos.TipoInvalido:
                    pass                              # el error se informa al revisar eventos_de_otros_contextos
            # Si el evento solo se recuerda, sus correspondencias {dato del comando: dato del evento} le dan al
            # comando un dato que llega con otro nombre (D2). Se revisan en eventos_de_otros_contextos.
            corr_ev = x.get("correspondencias") if "dispara" not in x and isinstance(x.get("correspondencias"), dict) else {}
            for local, del_ev in corr_ev.items():
                if isinstance(del_ev, str) and del_ev in datos_ev:
                    datos_ev[local] = datos_ev[del_ev]
            self.agregar(bolsa, datos_ev, f"{d} > requiere > {ev}")
            propios |= set(datos_ev)
            for k in datos_ev:
                origenes_cmd.setdefault(k, []).append(f'evento "{ev}"')

    def revisar_calculados_y_sas(self, n: str, m: dict, c: dict, d: str, crea: bool, todas: bool, bolsa: dict,
                                 propios: set, origenes_cmd: dict):
        """Las otras raíces que lee, sus datos calculados y los servicios SA que usa, en orden. Lo que dejan queda
        en la bolsa del comando."""
        sas, nombre_raiz = self.sas, self.rc["nombre"]
        # Otras raíces que el comando lee en el modelo (G6): se cargan por el dato con el nombre de su identidad.
        if not todas:
            for lt in m["lee_tambien"]:
                otra = self.raiz_por_id.get(lt["raiz_id"])
                if otra and otra["id_nombre"] not in bolsa:
                    self.error(d, f'lee también "{otra["nombre"]}" y para cargarla hace falta "{otra["id_nombre"]}", que el comando no tiene')

        # Datos calculados del comando: salen de una regla y se escriben a mano. Cada uno dice de qué datos sale
        # (de: datos por su nombre o una raíz que el comando tiene) y se calcula en cuanto están: antes de llamar a
        # los SA o después del SA que da el último. Quedan disponibles por su nombre para lo que sigue.
        raices_cmd = set()
        if not crea and not todas:
            raices_cmd.add(nombre_raiz)
        if not todas:
            raices_cmd |= {self.raiz_por_id[lt["raiz_id"]]["nombre"] for lt in m["lee_tambien"] if lt["raiz_id"] in self.raiz_por_id}
        calc_de, calc_t = {}, {}
        for k, x_c in self.mapa(c.get("calculados"), f"{d} > calculados").items():
            dc = f"{d} > calculados > {k}"
            x_c = self.mapa(x_c, dc, ["tipo", "de"], ["tipo", "de"])
            if k in (self.id_nombre, "estado"):
                self.error(dc, "la identidad y el estado no se calculan")
                continue
            t_c = self.tipo(x_c.get("tipo"), f"{dc} > tipo")
            if t_c:
                calc_t[k] = t_c
            calc_de[k] = [x for x in self.lista(x_c.get("de"), f"{dc} > de") if isinstance(x, str)]
            if not calc_de[k]:
                self.error(f"{dc} > de", "di de qué datos sale el calculado (o de qué raíz)")
        usos = [uso_sa(i) for i in self.lista(c.get("usa"), f"{d} > usa")]
        salidas_llamada = []
        for nombre_sa, op in usos:
            sal_map = op.get("salida") if isinstance(op.get("salida"), dict) else {}
            salidas_llamada.append({sal_map.get(k, k) for k in sas[nombre_sa]["salida"]} if nombre_sa in sas else set())
        puntos = ubicar_calculados(calc_de, set(bolsa) | raices_cmd, salidas_llamada)

        def calcular(lista_c):
            falla = False
            for k in lista_c:
                if k is None:                         # los que siguen no tienen sus datos en ningún momento
                    falla = True
                    continue
                if falla:
                    faltan = [x for x in calc_de[k] if x not in bolsa and x not in raices_cmd]
                    self.error(f"{d} > calculados > {k}", "sale de " + ", ".join(f'"{x}"' for x in faltan)
                               + ", que el comando no tiene (ni antes ni después de sus SA)")
                elif k in calc_t:
                    self.agregar(bolsa, {k: calc_t[k]}, f"{d} > calculados > {k}")
                    propios.add(k)
                    origenes_cmd.setdefault(k, []).append("calculado")

        # Servicios SA que usa, en orden: piden datos de la bolsa y le agregan su salida. Cada llamada puede fijar
        # datos de la entrada del SA (con), tomarlos de un dato con otro nombre (entrada), renombrar su salida
        # (salida) y hacerse solo si se cumple una condición (si, salvo): entonces su salida es opcional.
        calcular(puntos[0])
        for i, (sa, op) in enumerate(usos, 1):
            du = f"{d} > usa > {sa}"
            if sa not in sas:
                self.error(f"{d} > usa", f'"{sa}" no es un servicio SA del contexto')
                calcular(puntos[i])
                continue
            if not sas[sa]["llamable"]:
                self.error(du, "este SA no responde (solo recibe o envía): no se llama con usa")
                calcular(puntos[i])
                continue
            op = self.mapa(op, du, list(OPCIONES_USO_SA))
            sas[sa]["usado_por"].append(n)
            ent_sa = sas[sa]["entrada"]
            fijos = self.mapa(op.get("con"), f"{du} > con")
            for k, val in fijos.items():
                if k not in ent_sa:
                    self.error(f"{du} > con", f'"{k}" no está en la entrada del SA')
                elif not valor_valido(val, ent_sa[k]):
                    self.error(f"{du} > con", f'el valor {val!r} no es válido para "{k}" ({ent_sa[k]["tipo"]})')
            corr = self.mapa(op.get("entrada"), f"{du} > entrada")
            for k, dato in corr.items():
                if k not in ent_sa:
                    self.error(f"{du} > entrada", f'"{k}" no está en la entrada del SA')
                elif k in fijos:
                    self.error(f"{du} > entrada", f'"{k}" ya tiene un valor fijo en con')
                elif not isinstance(dato, str):
                    self.error(f"{du} > entrada", f'"{k}" se toma de un dato: escribe su nombre')
                else:
                    self.pide(bolsa, {dato: ent_sa[k]}, du, f'el servicio SA "{sa}" ("{k}")', propios)
            # Lo demás va por su nombre; un dato opcional del SA que el comando no tiene va en null.
            self.pide(bolsa, {k: tk for k, tk in ent_sa.items() if k not in fijos and k not in corr
                              and not (tk["opcional"] and k not in bolsa)}, du, f'el servicio SA "{sa}"', propios)
            self.si_salvo(op, bolsa, du, propios)
            condicional = "si" in op or "salvo" in op
            sal_map = self.mapa(op.get("salida"), f"{du} > salida")
            for k, nuevo in sal_map.items():
                if k not in sas[sa]["salida"]:
                    self.error(f"{du} > salida", f'"{k}" no está en la salida del SA')
                elif not isinstance(nuevo, str) or not nuevo.strip():
                    self.error(f"{du} > salida", f'"{k}" se renombra con un nombre de dato')
            salida = {}
            for k, tk in sas[sa]["salida"].items():
                nuevo = sal_map.get(k, k)
                if isinstance(nuevo, str):
                    salida[nuevo] = opcional(tk) if condicional else tk
            self.agregar(bolsa, salida, du)
            propios |= set(salida)
            for k in salida:
                origenes_cmd.setdefault(k, []).append(f'SA "{sa}"')
            calcular(puntos[i])

    def revisar_reglas(self, c: dict, d: str, todas: bool, bolsa: dict, propios: set):
        """Reglas del contrato declaradas en el YAML (reglas): una lista, en el orden en que se revisan. Cada una lleva
        su código (regla), su motivo y lo que pide de los datos del comando (entrada, raíz, servicios SA y calculados):
        exige {dato: [valores]} (el dato debe estar entre esos valores), rechaza {dato: [valores]} (no debe estar),
        con {dato: {comparación: valor}} en lugar de la lista para comparar un número o una fecha, y no_vacio [datos]
        (una lista con elementos, un texto que no está en blanco o un dato opcional que llegó)."""
        if "reglas" not in c:
            return
        if todas:
            self.error(f"{d} > reglas", "un comando sobre todas las raíces no lleva reglas: las elige su archivo manual")
            return
        for i, regla in enumerate(self.lista(c.get("reglas"), f"{d} > reglas"), 1):
            dr = f"{d} > reglas {i}"
            regla = self.mapa(regla, dr, ["regla", "exige", "rechaza", "no_vacio", "motivo"], ["regla", "motivo"])
            for k in ("regla", "motivo"):
                if k in regla and (not isinstance(regla[k], str) or not regla[k].strip()):
                    self.error(f"{dr} > {k}", "es un texto")
            if not any(k in regla for k in ("exige", "rechaza", "no_vacio")):
                self.error(dr, "di qué pide la regla: exige, rechaza o no_vacio")
            for k in ("exige", "rechaza"):
                pedidos = self.mapa(regla.get(k), f"{dr} > {k}")
                self.condicion({dato: x for dato, x in pedidos.items() if not isinstance(x, dict)}, bolsa, f"{dr} > {k}", propios)
                for dato, x in pedidos.items():
                    if isinstance(x, dict):
                        self.revisar_comparacion(dato, x, bolsa, propios, f"{dr} > {k}")
            for dato in self.lista(regla.get("no_vacio"), f"{dr} > no_vacio"):
                t = self.dato_de_regla(dato, bolsa, propios, f"{dr} > no_vacio")
                if t and not (t["lista"] or t["opcional"] or t["base"] == "string"):
                    self.error(f"{dr} > no_vacio", f'"{dato}" es {t["tipo"]}: no_vacio va con una lista, un texto o un dato opcional')

    def dato_de_regla(self, dato, bolsa: dict, propios: set, donde: str) -> dict | None:
        """El tipo de un dato que usa una regla, o None (con su error) si no está disponible o puede venir de dos lugares."""
        if dato in self.ambiguos and dato not in propios:
            self.error(donde, f'la regla usa "{dato}", que puede venir de {" y de ".join(self.ambiguos[dato])}')
        elif dato not in bolsa:
            self.error(donde, f'la regla usa "{dato}", que no está disponible')
        else:
            return bolsa[dato]
        return None

    def revisar_comparacion(self, dato, x: dict, bolsa: dict, propios: set, donde: str):
        """{dato: {comparación: valor}}: una sola comparación, de un número o una fecha con un valor fijo de su tipo."""
        t = self.dato_de_regla(dato, bolsa, propios, donde)
        if len(x) != 1 or next(iter(x)) not in COMPARACIONES:
            self.error(f"{donde} > {dato}", f'se escribe una lista de valores o una comparación: {", ".join(COMPARACIONES)}')
        elif t and (t["lista"] or t["base"] not in ("int", "decimal", "DateOnly", "DateTime")):
            self.error(f"{donde} > {dato}", f'"{dato}" es {t["tipo"]}: solo se comparan números y fechas')
        elif t and not valor_valido(next(iter(x.values())), {**t, "opcional": False}):
            self.error(f"{donde} > {dato}", f'el valor {next(iter(x.values()))!r} no es válido para "{dato}" ({t["tipo"]})')

    def revisar_eventos_del_comando(self, n: str, m: dict, c: dict, d: str, crea: bool, todas: bool, bolsa: dict,
                                    propios: set, guardados: dict, desde):
        """Los eventos del comando son exactamente los que dispara en el modelo: con eventos, o con resultados (un
        evento por resultado, cada uno con su condición, sus transiciones y lo que guarda)."""
        rc, ev_por_id, bolsas_evento = self.rc, self.ev_por_id, self.bolsas_evento
        todos, campos_raiz, vos, nombre_raiz = rc["todos"], rc["campos_raiz"], rc["vos"], rc["nombre"]
        base, estado_t = rc["base"], rc["estado_t"]
        lectura = m["acceso"] not in ESCRIBEN
        bolsas_resultado = {}                         # evento -> (bolsa, guardados, propios) de su resultado
        del_modelo = {ev_por_id[i] for i in m["eventos"]}
        if ("eventos" in c) == ("resultados" in c):
            self.error(d, "debe tener eventos o resultados (uno de los dos)")
            del_yaml = set()
        elif "eventos" in c:
            del_yaml = set(self.lista(c["eventos"], f"{d} > eventos"))
            if "a" in c and lectura:
                self.error(d, "el comando solo lee la raíz: no puede cambiar el estado (a)")
            if not crea and not todas and desde is None:
                self.error(d, "falta desde: los estados desde los que se permite el comando")
        else:
            res = self.mapa(c["resultados"], f"{d} > resultados")
            del_yaml = set(res)
            usados: dict[str, dict[str, set]] = {}
            for ev, rr in res.items():
                dr = f"{d} > resultados > {ev}"
                rr = self.mapa(rr, dr, ["si", "desde", "a", "valores", "guarda"], ["si"])
                # Lo que guarda y fija solo este resultado (además de lo del comando).
                bolsa_r, propios_r = dict(bolsa), set(propios)
                propios_r |= set(self.revisar_valores(rr.get("valores"), bolsa_r, f"{dr} > valores", todos))
                guarda_r = self.lista(rr.get("guarda"), f"{dr} > guarda")
                if guarda_r and m["acceso"] not in ESCRIBEN:
                    self.error(f"{dr} > guarda", f"el comando guarda datos pero en el modelo su acceso a la raíz es de {m['acceso']}")
                guardados_r = self.revisar_guarda(guarda_r, bolsa_r, propios_r, f"{dr} > guarda", campos_raiz, vos, nombre_raiz)
                bolsas_resultado[ev] = (bolsa_r, {**guardados, **guardados_r}, propios_r)
                for campo, vals in self.condicion(rr.get("si"), bolsa, f"{dr} > si", propios).items():
                    for otro, vals_otro in usados.get(campo, {}).items():
                        if vals & vals_otro:
                            self.error(dr, f'su condición se cruza con la de "{otro}" en {sorted(vals & vals_otro)}')
                    usados.setdefault(campo, {})[ev] = vals
                if "desde" in rr:
                    self.estados_validos(rr["desde"], f"{dr} > desde")
                elif desde is None:
                    self.error(dr, "falta desde, en el resultado o en el comando")
                if "a" in rr:
                    self.estados_validos(rr["a"], f"{dr} > a")
                    if lectura:
                        self.error(dr, "el comando solo lee la raíz: no puede cambiar el estado (a)")
            for campo, por_ev in usados.items():
                t = bolsa.get(campo)
                if t and t["enum"]:
                    falta = set(t["enum"]["valores"]) - set().union(*por_ev.values())
                    if falta:
                        self.aviso(d, f'ningún resultado cubre {sorted(falta)} de "{campo}"')
        for ev in sorted(del_modelo - del_yaml):
            self.error(d, f'en el modelo dispara "{ev}" y el YAML no lo declara')
        for ev in sorted(del_yaml - del_modelo):
            self.error(d, f'el YAML declara "{ev}" y en el modelo el comando no lo dispara')

        for ev in del_yaml & del_modelo:
            bolsa_e, guardados_e, propios_e = bolsas_resultado.get(ev, (bolsa, guardados, propios))
            bolsa_ev = dict(bolsa_e)
            self.agregar(bolsa_ev, guardados_e, d)
            if crea:                   # después de guardar ya hay identidad y estado
                bolsa_ev.update(base)
                if estado_t:
                    bolsa_ev["estado"] = estado_t
            bolsas_evento.setdefault(ev, []).append((n, bolsa_ev, frozenset(propios_e), self.rc["nombre"]))

    def revisar_temporizador(self, x, ent: dict, d: str):
        """temporizador: {cada minutos: N, con: {dato: valor}, ahora: dato}. El comando corre solo cada N minutos con
        los valores de con y la hora actual en el dato de ahora; todo dato obligatorio de su entrada debe quedar cubierto."""
        x = self.mapa(x, d, ["cada minutos", "con", "ahora"], ["cada minutos"])
        cada = x.get("cada minutos")
        if not isinstance(cada, int) or isinstance(cada, bool) or cada < 1:
            self.error(d, "cada minutos es un entero mayor que 0")
        cubiertos = set()
        for k, v in self.mapa(x.get("con"), f"{d} > con").items():
            if k not in ent:
                self.error(f"{d} > con", f'"{k}" no está en la entrada del comando')
            elif not valor_valido(v, ent[k]):
                self.error(f"{d} > con", f'el valor {v!r} no es válido para "{k}" ({ent[k]["tipo"]})')
            cubiertos.add(k)
        if "ahora" in x:
            ahora = x["ahora"]
            if ahora not in ent or ent[ahora]["base"] != "DateTime" or ent[ahora]["lista"]:
                self.error(f"{d} > ahora", f'"{ahora}" debe ser un dato DateTime de la entrada')
            cubiertos.add(ahora)
        for k, t in ent.items():
            if not t["opcional"] and k not in cubiertos:
                self.error(d, f'el comando necesita "{k}" y el temporizador no lo da (con o ahora)')

    OPERACIONES_LISTA = ("agregar", "reemplazar", "quitar")

    def revisar_guarda(self, guarda: list, bolsa: dict, propios: set, d: str, campos_raiz: dict, vos: dict,
                       nombre_raiz: str) -> dict:
        """Lo que se guarda en la raíz: objetos de valor y campos por su nombre, {campo: dato} para guardar un dato
        con otro nombre, y en un objeto de valor con Cardinalidad Muchos (G4) {lista: agregar}, {lista: {reemplazar:
        [claves]}} o {lista: {quitar: [claves]}}. Cada dato debe tener un solo destino. Devuelve lo guardado."""
        guardados, destinos = {}, {}

        def pedir_vo(v, solo=None, cubiertos=frozenset()):
            for campo in v["campos"]:
                if solo is not None and campo["nombre"] not in solo or campo["nombre"] in cubiertos:
                    continue
                # Una lista que el comando no tiene queda vacía; un dato opcional que no tiene, en null.
                vacio = campo["opcional"] or tipos.interpretar(campo["tipo"])["lista"]
                if campo["nombre"] in bolsa or not vacio or solo is not None:
                    self.pide(bolsa, {campo["nombre"]: campo}, d, f'el objeto de valor "{v["nombre"]}"', propios)

        for g in guarda:
            if isinstance(g, dict) and len(g) == 1 and next(iter(g)) in vos:     # operación sobre una lista
                nombre_vo, op = next(iter(g.items()))
                v = vos[nombre_vo]
                if v["cardinalidad"] != "Muchos":
                    self.error(d, f'"{nombre_vo}" tiene Cardinalidad {v["cardinalidad"]}: se guarda por su nombre, sin operación')
                    continue
                if op == "agregar":
                    claves = None
                elif isinstance(op, dict) and "agregar" in op:
                    # {lista: {agregar: {campo: dato}, valores: {campo: valor}, si: ..., salvo: ...}}: agrega un elemento
                    # con datos de otro nombre y valores fijos, y solo si se cumple la condición. Puede repetirse.
                    self.revisar_agregar(op, v, bolsa, propios, f"{d} > {nombre_vo}", pedir_vo)
                    for campo in v["campos"]:
                        guardados[campo["nombre"]] = campo
                    continue
                elif isinstance(op, dict) and len(op) == 1 and next(iter(op)) == "todos":
                    # {lista: {todos: dato}}: la lista entera se reemplaza con un dato de tipo List<objeto de valor>.
                    dato = op["todos"]
                    if not isinstance(dato, str) or dato not in bolsa:
                        self.error(d, f'"{nombre_vo}" se guarda entera con "{dato}", que el comando no tiene')
                    elif bolsa[dato].get("objeto") != nombre_vo or not bolsa[dato]["lista"]:
                        self.error(d, f'"{dato}" es {bolsa[dato]["tipo"]}; para guardar "{nombre_vo}" entera debe ser List<{nombre_vo}>')
                    destinos.setdefault(nombre_vo, []).append("todos")
                    continue
                elif isinstance(op, dict) and len(op) == 1 and next(iter(op)) in ("reemplazar", "quitar"):
                    op, claves = next(iter(op.items()))
                    claves = self.lista(claves, f"{d} > {nombre_vo} > {op}")
                    nombres_vo = {c["nombre"] for c in v["campos"]}
                    for k in claves:
                        if k not in nombres_vo:
                            self.error(d, f'la clave "{k}" no es un campo de "{nombre_vo}"')
                    if not claves:
                        self.error(d, f'{op} necesita la clave: los campos con que se encuentra el elemento de "{nombre_vo}"')
                else:
                    self.error(d, f'en "{nombre_vo}" (una lista) se escribe agregar, {{agregar: {{campo: dato}}, valores: ...}}, '
                                  f'{{reemplazar: [claves]}}, {{quitar: [claves]}} o {{todos: dato}}')
                    continue
                pedir_vo(v, solo=set(claves) if op == "quitar" else None)
                if op != "quitar":
                    for campo in v["campos"]:
                        guardados[campo["nombre"]] = campo
                destinos.setdefault(nombre_vo, []).append(op)
            elif isinstance(g, dict):                     # {campo de la raíz: dato}: guarda un dato con otro nombre
                if len(g) != 1:
                    self.error(d, "una correspondencia es {campo de la raíz: dato}, una por línea")
                    continue
                campo, dato = next(iter(g.items()))
                if campo not in campos_raiz:
                    self.error(d, f'"{campo}" no es un campo de la raíz {nombre_raiz} ni un objeto de valor')
                    continue
                if not isinstance(dato, str) or dato not in bolsa:
                    self.error(d, f'"{campo}" se guarda con "{dato}", que el comando no tiene')
                elif not mismo_tipo(bolsa[dato], campos_raiz[campo]):
                    self.error(d, f'"{dato}" es {bolsa[dato]["tipo"]} y "{campo}" es {campos_raiz[campo]["tipo"]}')
                guardados[campo] = campos_raiz[campo]
                destinos.setdefault(campo, []).append(f'la raíz "{nombre_raiz}"')
            elif not isinstance(g, str):
                self.error(d, f"{g!r} no es un nombre, una correspondencia ni una operación sobre una lista")
            elif g in vos:
                v = vos[g]
                if v["cardinalidad"] == "Muchos":
                    self.error(d, f'"{g}" tiene Cardinalidad Muchos: se escribe {{{g}: agregar}}, {{{g}: {{reemplazar: [claves]}}}} '
                                  f'o {{{g}: {{quitar: [claves]}}}}')
                    continue
                pedir_vo(v)
                for campo in v["campos"]:
                    guardados[campo["nombre"]] = campo
                    destinos.setdefault(campo["nombre"], []).append(f'"{g}"')
            elif g in campos_raiz:
                self.pide(bolsa, {g: campos_raiz[g]}, d, f'el campo "{g}" de la raíz', propios)
                guardados[g] = campos_raiz[g]
                destinos.setdefault(g, []).append(f'la raíz "{nombre_raiz}"')
            else:
                self.error(d, f'"{g}" no es un objeto de valor ni un campo de la raíz {nombre_raiz}')
        for nombre_dato, lugares in sorted(destinos.items()):
            if len(lugares) > 1:
                self.error(d, f'"{nombre_dato}" puede ir a más de un destino: {" y ".join(lugares)}')
        return guardados

    def revisar_agregar(self, op: dict, v: dict, bolsa: dict, propios: set, d: str, pedir_vo):
        """{agregar: {campo: dato}, valores: {campo: valor}, si, salvo}: cada campo sale de una correspondencia, de un
        valor fijo o del dato con su nombre."""
        op = self.mapa(op, d, ["agregar", "valores", "si", "salvo"], ["agregar"])
        campos = {c["nombre"]: c for c in v["campos"]}
        cubiertos = set()
        for campo, dato in self.mapa(op.get("agregar"), f"{d} > agregar").items():
            if campo not in campos:
                self.error(f"{d} > agregar", f'"{campo}" no es un campo de "{v["nombre"]}"')
            elif not isinstance(dato, str) or dato not in bolsa:
                self.error(f"{d} > agregar", f'"{campo}" se guarda con "{dato}", que el comando no tiene')
            elif not mismo_tipo(bolsa[dato], tipos.interpretar(campos[campo]["tipo"])):
                self.error(f"{d} > agregar", f'"{dato}" es {bolsa[dato]["tipo"]} y "{campo}" es {campos[campo]["tipo"]}')
            cubiertos.add(campo)
        for campo, valor in self.mapa(op.get("valores"), f"{d} > valores").items():
            if campo not in campos:
                self.error(f"{d} > valores", f'"{campo}" no es un campo de "{v["nombre"]}"')
            elif campo in cubiertos:
                self.error(f"{d} > valores", f'"{campo}" ya tiene una correspondencia en agregar')
            elif not valor_valido(valor, tipos.interpretar(campos[campo]["tipo"])):
                self.error(f"{d} > valores", f'el valor {valor!r} no es válido para "{campo}" ({campos[campo]["tipo"]})')
            cubiertos.add(campo)
        self.si_salvo(op, bolsa, d, propios)
        pedir_vo(v, cubiertos=frozenset(cubiertos))
