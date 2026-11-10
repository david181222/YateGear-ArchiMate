"""Comandos: el record, el manejador y el archivo manual de cada uno."""
from __future__ import annotations

from comun import nombres, tipos
from generacion.csharp import (
    Ambito,
    cs_cadena,
    cs_literal,
    cs_tipo,
    descripcion_del_contrato,
    ErrorDeGeneracion,
    fuente,
    lineas,
    provisional,
)
from validacion import valores


class Comandos:
    """Prepara los comandos del contexto."""

    def preparar_comandos(self):
        self.comandos = []
        ev_por_id = {e["id"]: e["nombre"] for e in self.ctx["eventos"]}
        for mc in self.ctx["comandos"]:
            self.preparar_comando(mc, ev_por_id)

    def preparar_comando(self, mc: dict, ev_por_id: dict):
        r = self.usar_raiz(mc["raiz_id"])          # la raíz del agregado del comando (G2)
        v = r["var"]
        sc = self.s["comandos"][mc["nombre"]]
        clase = nombres.pascal(mc["nombre"])
        n = {k: self.tipo_cs_nuevo(x, f'comando "{mc["nombre"]}"') for k, x in
             {"clase": clase, "datos": f"{clase}Datos", "manejador": f"{clase}Manejador"}.items()}
        crea = sc.get("crea") is True
        si_no_existe = sc.get("crea") == "si_no_existe"   # carga la raíz y, si no existe, la crea vacía
        todas = sc.get("sobre") == "todas"            # G8: elige raíces y publica un evento por cada una

        def estado(nombre_estado):                # literal de C# de un estado de la raíz
            return f'{r["estado_clase"]}.{nombres.pascal(nombre_estado)}'

        ent = self.campos(sc.get("entrada"), f'entrada de "{mc["nombre"]}" (YAML)')
        params = ([] if crea or todas else [{"cs": "string", "prop": r["id_prop"]}]) + ent
        self.revisar_miembros(clase, [p["prop"] for p in params])
        capa_ent = {c["nombre"]: fuente(f'comando.{c["prop"]}', c["tipo"]) for c in ent}

        antes = Ambito()                       # antes de guardar
        if not crea and not todas:
            antes.agregar(dict(self.fuentes_raiz))
        antes.agregar(capa_ent)
        # Valores fijos del comando (YAML: valores).
        capa_val = {k: fuente(cs_literal(x, self.tipos_raiz[k]), self.tipos_raiz[k])
                    for k, x in (sc.get("valores") or {}).items()}
        antes.agregar(capa_val)
        llamadas, deps, datos_props, datos_args = [], [], [], ["comando"]
        datos_props.append({"cs": clase, "prop": "Comando"})
        otras = [self.raices[self.usar_raiz(x["raiz_id"])["nombre"]]["raiz"] for x in mc["lee_tambien"]]
        self.usar_raiz(mc["raiz_id"])
        if todas:                                  # todas las raíces, y las demás que lee (G8)
            datos_props.append({"cs": f'IReadOnlyList<{r["clase"]}>', "prop": "Raices"})
            datos_args.append("raices")
            for o in otras:
                datos_props.append({"cs": f'IReadOnlyList<{o["clase"]}>', "prop": o["clase"]})
                datos_args.append(f'{o["repositorio"]}.Todas()')
        elif not crea:
            datos_props.append({"cs": r["clase"], "prop": r["clase"]})
            datos_args.append(v)
        requeridos, capas_req = self.eventos_requeridos(sc, r, antes, datos_props, datos_args)
        if requeridos:
            deps.append({"cs": "MemoriaDeEventos", "var": "memoria"})
        # Otras raíces que el comando lee (G6): se cargan por el dato con el nombre de su identidad; 404 si no existen.
        leidas = []
        for o in otras:
            deps.append({"cs": f'Repositorio<{o["clase"]}>', "var": o["repositorio"]})
            if todas:
                continue
            leidas.append({"var": o["var"], "repositorio": o["repositorio"], "clase": o["clase"],
                           "identidad": antes.expr(o["id_nombre"], False), "nombre": o["nombre"].lower()})
            datos_props.append({"cs": o["clase"], "prop": o["clase"]})
            datos_args.append(o["var"])
        # Servicios SA que usa, en orden, y datos calculados del comando (a mano): cada calculado se calcula en
        # cuanto están los datos de los que sale (valores.ubicar_calculados), antes de los SA o después del que da el
        # último. Una llamada puede fijar datos de la entrada (con), tomarlos con otro nombre (entrada), renombrar
        # su salida (salida) y hacerse solo si se cumple una condición (si, salvo).
        capas_sa, capa_calc, calc_metodos = [], {}, []
        calc_y = sc.get("calculados") or {}
        calc_de = {k: list(x["de"]) for k, x in calc_y.items()}
        usos = [valores.uso_sa(i) for i in sc.get("usa") or []]
        veces = {}
        for nombre_sa, _ in usos:
            veces[nombre_sa] = veces.get(nombre_sa, 0) + 1
        salidas = [{(op.get("salida") or {}).get(c["nombre"], c["nombre"]) for c in self.sas[s_]["salida_campos"]}
                   for s_, op in usos]
        raices_cmd = {} if crea or todas else {r["nombre"]: r}
        if not todas:
            raices_cmd.update({o["nombre"]: o for o in otras})
        disponibles = set().union(*(set(capa) for capa in antes.capas)) | set(raices_cmd)
        puntos = valores.ubicar_calculados(calc_de, disponibles, salidas)
        if None in puntos[-1]:
            raise ErrorDeGeneracion(f'"{mc["nombre"]}": hay calculados sin sus datos (revisa el YAML con valores.py)')

        def calcular(lista_c):
            for k in lista_c:
                t = self.tipo(calc_y[k]["tipo"], f'calculado "{k}" de "{mc["nombre"]}" (YAML)')
                var_c = "calculado" + nombres.pascal(k)
                params, args_c = [], []
                for x in calc_de[k]:
                    if x in raices_cmd:               # una raíz entera
                        params.append(f'{raices_cmd[x]["clase"]} {nombres.variable(x)}')
                        args_c.append(raices_cmd[x]["var"])
                    else:
                        f = antes.buscar(x)
                        params.append(f'{cs_tipo(f["tipo"])} {nombres.variable(x)}')
                        args_c.append(antes.expr(x, f["tipo"]["opcional"]))
                llamadas.append({"tipo": "calculo", "var": var_c, "metodo": nombres.pascal(k), "args": args_c})
                calc_metodos.append({"nombre": k, "metodo": nombres.pascal(k), "cs": cs_tipo(t), "params": params,
                                     "de": calc_de[k], "tipo_yaml": calc_y[k]["tipo"], "provisional": provisional(t)})
                capa = {k: fuente(var_c, t)}
                antes.agregar(capa)
                capa_calc.update(capa)
                datos_props.append({"cs": cs_tipo(t), "prop": nombres.pascal(k)})
                datos_args.append(var_c)

        calcular(puntos[0])
        vez = {}
        for i, (nombre_sa, op) in enumerate(usos, 1):
            sa = self.sas[nombre_sa]
            vez[nombre_sa] = vez.get(nombre_sa, 0) + 1
            sufijo = str(vez[nombre_sa]) if veces[nombre_sa] > 1 else ""
            con_sa, corr, sal_map = op.get("con") or {}, op.get("entrada") or {}, op.get("salida") or {}
            args = []
            for c in sa["entrada_campos"]:
                dato = corr.get(c["nombre"], c["nombre"])
                if c["nombre"] in con_sa:
                    args.append(cs_literal(con_sa[c["nombre"]], c["tipo"]))
                elif antes.buscar(dato) is None and c["tipo"]["opcional"]:
                    args.append("null")               # un dato opcional del SA que el comando no tiene
                else:
                    args.append(antes.expr(dato, c["tipo"]["opcional"]))
            var_resp = "respuesta" + sa["clase"] + sufijo
            cond = self.condicion(op, antes)
            llamadas.append({"tipo": "llamada", "var": var_resp, "servicio": sa["var"], "entrada": sa["entrada"],
                             "salida": sa["salida"], "args": args, "condicion": cond})
            if sa["var"] not in [d["var"] for d in deps]:
                deps.append({"cs": sa["interfaz"], "var": sa["var"]})
            if cond:                                 # si no se llamó, su salida es null
                capa = {sal_map.get(c["nombre"], c["nombre"]): fuente(f'{var_resp}?.{c["prop"]}', valores.opcional(c["tipo"]))
                        for c in sa["salida_campos"]}
            else:
                capa = {sal_map.get(c["nombre"], c["nombre"]): fuente(f'{var_resp}.{c["prop"]}', c["tipo"])
                        for c in sa["salida_campos"]}
            antes.agregar(capa)
            capas_sa.append(capa)
            datos_props.append({"cs": sa["salida"] + ("?" if cond else ""), "prop": sa["clase"] + sufijo})
            datos_args.append(var_resp)
            calcular(puntos[i])

        resultados, enum_res = [], None
        eventos_cmd = []
        if sc.get("resultados"):
            enum_res = self.tipo_cs_nuevo(f"{clase}Resultado", f'resultados de "{mc["nombre"]}"')
            for ev, rr in sc["resultados"].items():
                partes = []
                for campo, vals in rr["si"].items():
                    f = antes.buscar(campo)
                    t = {**f["tipo"], "opcional": False}
                    e = antes.expr(campo, True)
                    partes.append("(" + " || ".join(f"{e} == {cs_literal(x, t)}" for x in vals) + ")")
                resultados.append({"miembro": nombres.pascal(ev), "evento": ev, "condicion": " && ".join(partes),
                                   "desde": [estado(x) for x in rr.get("desde") or []],
                                   "a": estado(rr["a"]) if rr.get("a") else None,
                                   "operacion": cs_cadena(f'{mc["nombre"]}: {ev}')})
                eventos_cmd.append(ev)
            self.revisar_miembros(enum_res, [x["miembro"] for x in resultados])
            datos_props.append({"cs": enum_res, "prop": "Resultado"})
            datos_args.append("resultado")
        else:
            eventos_cmd = list(sc.get("eventos") or [])
        self.revisar_miembros(n["datos"], [p["prop"] for p in datos_props])

        # Lo que guarda (después de ValidarReglas): el comando y, si tiene resultados, cada resultado.
        asignaciones, operaciones = self.guardar(sc.get("guarda"), antes, r)
        if crea:
            asignaciones.insert(0, {"prop": "Estado", "expr": f'{r["estado_clase"]}.{nombres.pascal(sc["a"])}'})
        capas_val_r = {}
        for x in resultados:
            rr = sc["resultados"][x["evento"]]
            capas_val_r[x["evento"]] = {k: fuente(cs_literal(val, self.tipos_raiz[k]), self.tipos_raiz[k])
                                        for k, val in (rr.get("valores") or {}).items()}
            x["asignaciones"], x["operaciones"] = self.guardar(rr.get("guarda"), antes.con(capas_val_r[x["evento"]]), r)

        identidad_expr, partes_obligatorias = self.identidad_con_datos(r, crea, antes, asignaciones)
        # Eventos (después de guardar: ya hay raíz e identidad).
        publicar, calculados = self.publicaciones(r, eventos_cmd, [capa_ent, capa_val] + capas_req + capas_sa + [capa_calc],
                                                  capas_val_r)
        for x in resultados:
            x["publicar"] = [publicar[x["evento"]]]
        self.revisar_miembros(n["manejador"], [k["metodo"] for k in calculados + calc_metodos])
        eventos_modelo = sorted(ev_por_id[i] for i in mc["eventos"])
        if sorted(eventos_cmd) != eventos_modelo:
            raise ErrorDeGeneracion(f'"{mc["nombre"]}": los eventos del YAML no son los del modelo')

        k = mc["contrato"]
        com = {**n, "nombre": mc["nombre"], "codigo": mc["codigo"], "id": mc["id"], "crea": crea,
               "parametros": params, "datos_props": datos_props, "datos_args": datos_args,
               "dependencias": [{"cs": f'Repositorio<{r["clase"]}>', "var": "repositorio"},
                                {"cs": "BusDeEventos", "var": "bus"}] + deps,
               "llamadas": llamadas, "resultados": resultados, "enum_resultado": enum_res,
               "requeridos": requeridos, "identidad_expr": identidad_expr, "operaciones": operaciones,
               "leidas": leidas, "todas": todas, "temporizador": self.temporizador(sc, clase, n, ent) if todas else None,
               "raiz_nombre": r["nombre"], "si_no_existe": si_no_existe,
               "id_cadena": cs_cadena(r["id_nombre"]), "partes_obligatorias": partes_obligatorias, "estado_inicial": estado(self.raiz["estado_t"]["enum"]["valores"][0]),
               "resultados_con_guarda": [x for x in resultados if x["asignaciones"] or x["operaciones"]],
               "operacion": cs_cadena(mc["nombre"]),
               "desde": [] if crea else [estado(x) for x in sc.get("desde") or []],
               "a": estado(sc["a"]) if sc.get("a") and not crea else None,
               "resultados_con_desde": [x for x in resultados if x["desde"]],
               "resultados_con_a": [x for x in resultados if x["a"]],
               "sin_resultado": cs_cadena(f'Ningún resultado de "{mc["nombre"]}" se cumple con estos datos.'),
               "escribe": crea or si_no_existe or mc["acceso"] in ("escritura", "lectura y escritura"),
               "asignaciones": asignaciones, "eventos": [publicar[e] for e in eventos_cmd],
               "calculados": calculados, "calculados_comando": calc_metodos,
               "con_calculos": any(x["tipo"] == "calculo" for x in llamadas),
               "contrato": k, "servicio_negocio": mc["servicio_negocio"],
               "reglas": lineas(k["reglas"]) if k["reglas"] else ["El contrato no tiene reglas."],
               "salida_contrato": lineas(k["salida"]),
               "ruta": f'{self.ruta_base}/comandos/{nombres.ruta(mc["nombre"])}',
               "resumen": f'Comando {mc["codigo"]}: {mc["nombre"]}', "descripcion": descripcion_del_contrato(k),
               "archivo": f'{self.proyecto}/Comandos/{clase}.g.cs',
               "manual": f'{self.proyecto}/Comandos/{clase}.cs', "spec": sc, "entrada_campos": ent}
        self.comandos.append(com)
        cab = self.cabecera("ApplicationProcess", mc["nombre"], mc["id"], mc["codigo"])
        self.render("comando.g.cs.j2", com["archivo"], c=com, raiz=r, cabecera=cab)
        self.render("comando_manual.cs.j2", com["manual"], manual=True, c=com, raiz=r, cabecera=cab)
        self.trazar_comando(mc, com, n, r)

    def eventos_requeridos(self, sc: dict, r: dict, antes: Ambito, datos_props: list, datos_args: list):
        """Eventos de otros contextos que el comando requiere (YAML: requiere): se buscan en la memoria por su
        identidad, y sus datos quedan disponibles para el comando. Devuelve los requeridos y la capa de datos de cada uno."""
        requeridos, capas_req = [], []
        for nombre_ev in sc.get("requiere") or []:
            x = self.s["eventos_de_otros_contextos"][nombre_ev]
            ev_clase, var_ev = nombres.pascal(nombre_ev), nombres.variable_local(nombre_ev)
            id_ev = x.get("identidad") or r["id_nombre"]
            requeridos.append({"var": var_ev, "clase": ev_clase, "nombre": cs_cadena(nombre_ev),
                               "identidad": antes.expr(id_ev, False)})
            capa = {k: fuente(f"{var_ev}.{nombres.pascal(k)}", tipos.interpretar(tx))
                    for k, tx in (x.get("datos") or {}).items()}
            # Un evento que solo se recuerda puede traer un dato con otro nombre (correspondencias, D2): el comando
            # lo toma con su nombre, {dato del comando: dato del evento}.
            if "dispara" not in x:
                for local, del_ev in (x.get("correspondencias") or {}).items():
                    capa[local] = fuente(f"{var_ev}.{nombres.pascal(del_ev)}", tipos.interpretar(x["datos"][del_ev]))
            antes.agregar(capa)
            capas_req.append(capa)
            datos_props.append({"cs": ev_clase, "prop": ev_clase})
            datos_args.append(var_ev)
        return requeridos, capas_req

    def identidad_con_datos(self, r: dict, crea: bool, antes: Ambito, asignaciones: list):
        """Identidad formada con datos: sus partes que no son campos se guardan en la raíz (se agregan a asignaciones),
        y la identidad se arma uniéndolas con "/". Al agregarla, el repositorio responde 409 si ya existe.
        Devuelve la expresión de la identidad (None si es un consecutivo o el comando no crea) y sus partes obligatorias."""
        identidad_expr, partes_obligatorias = None, []
        if crea and not r["consecutivo"]:
            # Las partes de texto que llegan en la entrada no pueden faltar (si no, la identidad quedaría a medias).
            for parte in r["id_de"]:
                f_parte = antes.buscar(parte)
                if f_parte and f_parte["tipo"]["base"] == "string" and f_parte["requerido"].startswith("comando."):
                    partes_obligatorias.append({"expr": f_parte["requerido"], "nombre": cs_cadena(parte)})
            for comp in r["componentes"]:
                asignaciones.append({"prop": comp["prop"], "expr": antes.expr(comp["nombre"], False)})
            partes = []
            for parte in r["id_de"]:
                fuente_parte = antes.buscar(parte)
                if fuente_parte is None:              # campo de la raíz que solo se guarda: se toma de la raíz nueva
                    fuente_parte = self.fuentes_raiz[parte]
                    e = fuente_parte["requerido"]
                else:
                    e = antes.expr(parte, False)
                # Las fechas, en formato fijo e independiente del idioma del equipo (2026-03-10T10:00:00).
                formato = {"DateTime": '"s"', "DateOnly": '"yyyy-MM-dd"'}.get(fuente_parte["tipo"]["base"])
                partes.append(f"({e}).ToString({formato}, System.Globalization.CultureInfo.InvariantCulture)" if formato else e)
            identidad_expr = '$"' + "/".join("{(" + x + ")}" for x in partes) + '"'
        return identidad_expr, partes_obligatorias

    def publicaciones(self, r: dict, eventos_cmd: list[str], capas: list[dict], capas_val_r: dict):
        """Los eventos que publica el comando, con sus argumentos, y los datos calculados de esos eventos (a mano).
        capas: los datos disponibles después de guardar, además de los de la raíz; la última gana."""
        v = r["var"]
        despues = Ambito()
        despues.agregar(dict(self.fuentes_raiz))
        for capa in capas:
            despues.agregar(capa)
        calculados, vistos = [], set()
        publicar = {}
        for nombre_ev in eventos_cmd:
            ev = self.eventos[nombre_ev]
            amb_ev = despues.con(capas_val_r.get(nombre_ev, {}))     # con los valores de su resultado
            args = [f'{v}.{r["id_prop"]}']
            args += [amb_ev.expr(d["nombre"], d["tipo"]["opcional"]) for d in ev["datos"]]
            for k in ev["calculados"]:
                if k["prop"] not in vistos:
                    vistos.add(k["prop"])
                    calculados.append({"nombre": k["nombre"], "metodo": k["prop"], "cs": k["cs"],
                                       "tipo_yaml": k["tipo"]["tipo"], "evento": nombre_ev,
                                       "provisional": provisional(k["tipo"])})
                args.append(f'{k["prop"]}(datos)')
            publicar[nombre_ev] = {"clase": ev["clase"], "args": args}
        return publicar, calculados

    def trazar_comando(self, mc: dict, com: dict, n: dict, r: dict):
        """Las filas de trazabilidad del comando: su proceso, sus accesos, su servicio de negocio y su contrato."""
        k = mc["contrato"]
        for x in ("clase", "datos", "manejador"):
            self.traza_de(mc["id"], "ApplicationProcess", mc["nombre"], com["archivo"], n[x])
        self.traza_de(mc["id"], "ApplicationProcess", mc["nombre"], com["manual"], f'{n["manejador"]} (manual)')
        self.traza_de(mc["id"], "ApplicationProcess", mc["nombre"], f"{self.proyecto}/Registro.g.cs", f'POST {com["ruta"]}')
        if mc["acceso_id"]:
            self.traza_de(mc["acceso_id"], "Access", f'{mc["nombre"]} -> {r["nombre"]} ({mc["acceso"]})', com["archivo"], n["manejador"])
        for lt in mc["lee_tambien"]:
            self.traza_de(lt["acceso_id"], "Access", f'{mc["nombre"]} -> otra raíz (lectura)', com["archivo"], n["manejador"])
        self.traza_de(mc["servicio_negocio"]["id"], "BusinessService", mc["servicio_negocio"]["nombre"], com["archivo"], n["manejador"])
        self.traza_de(k["id"], "Contract", k["nombre"], com["archivo"], n["manejador"])
        self.traza_de(k["id"], "Contract", k["nombre"], com["manual"], f'{n["manejador"]}.ValidarReglas (manual)')

    def temporizador(self, sc: dict, clase: str, n: dict, ent: list[dict]) -> dict | None:
        """El temporizador de un comando sobre todas (G8, YAML: temporizador): corre el comando cada N minutos con
        los valores de con y la hora actual en el dato de ahora."""
        x = sc.get("temporizador")
        if not x:
            return None
        nombre = self.tipo_cs_nuevo(f"{clase}Temporizador", f'temporizador de "{clase}"')
        con, ahora = x.get("con") or {}, x.get("ahora")
        args = [cs_literal(con[c["nombre"]], c["tipo"]) if c["nombre"] in con else "DateTime.Now" if c["nombre"] == ahora
                else "null" for c in ent]
        return {"clase": nombre, "minutos": x["cada minutos"], "args": args, "manejador": n["manejador"], "comando": clase}

    @staticmethod
    def condicion(x: dict, amb: Ambito) -> str | None:
        """Expresión de C# de las condiciones si (el dato está entre esos valores) y salvo (no está) de x, o None."""
        partes = []
        for clave, negada in (("si", False), ("salvo", True)):
            for campo, vals in (x.get(clave) or {}).items():
                f = amb.buscar(campo)
                if f is None:
                    raise ErrorDeGeneracion(f'la condición usa "{campo}", que no está disponible')
                t = {**f["tipo"], "opcional": False}
                e = amb.expr(campo, True)
                o = "(" + " || ".join(f"{e} == {cs_literal(val, t)}" for val in vals) + ")"
                partes.append(f"!{o}" if negada else o)
        return " && ".join(partes) or None

    def condicion_disparo(self, op: dict, amb: Ambito, rc: dict, id_raiz: str, dependencias: dict) -> str | None:
        """La condición de un comando que dispara un evento o un mensaje: si y salvo, y con si_existe, que su raíz exista
        (si no existe, el evento no le aplica y el comando no corre). Agrega a dependencias el repositorio que hace falta."""
        cond = self.condicion(op, amb)
        if not op.get("si_existe"):
            return cond
        dependencias[rc["repositorio"]] = {"cs": f'Repositorio<{rc["clase"]}>', "var": rc["repositorio"]}
        existe = f'{rc["repositorio"]}.Obtener({id_raiz}) is not null'
        return f"{existe} && {cond}" if cond else existe

    def guardar(self, guarda, amb: Ambito, r: dict) -> tuple[list[dict], list[str]]:
        """Lo que escribe en la raíz (YAML: guarda). Devuelve las asignaciones (propiedad = expresión) y las
        operaciones sobre listas (sentencias de C#) de los objetos de valor con Cardinalidad Muchos (G4)."""
        asignaciones, operaciones = [], []
        v = r["var"]

        def nuevo(vo, corr=None, valores=None):
            args = []
            for c in vo["campos"]:
                dato = (corr or {}).get(c["nombre"], c["nombre"])
                if c["nombre"] in (valores or {}):
                    args.append(cs_literal(valores[c["nombre"]], c["tipo"]))
                elif amb.buscar(dato):
                    args.append(amb.expr(dato, c["tipo"]["opcional"]))
                else:                                    # una lista que no llega queda vacía; lo opcional, en null
                    args.append("[]" if c["tipo"]["lista"] and not c["tipo"]["opcional"] else "null")
            return f'new {vo["clase"]}({", ".join(args)})'

        def agregar(vo, lista, elemento):
            return f"Entidades.Agregar({lista}, {elemento});" if vo["entidad"] else f"{lista}.Add({elemento});"

        for g in guarda or []:
            if isinstance(g, dict) and next(iter(g)) in self.vos:      # operación sobre una lista
                nombre_vo, op = next(iter(g.items()))
                vo = self.vos[nombre_vo]
                lista = f'{v}.{vo["prop"]}'
                if op == "agregar":
                    operaciones.append(agregar(vo, lista, nuevo(vo)))
                    continue
                if isinstance(op, dict) and "agregar" in op:     # con correspondencias, valores fijos y condición
                    sentencia = agregar(vo, lista, nuevo(vo, op.get("agregar") or {}, op.get("valores") or {}))
                    cond = self.condicion(op, amb)
                    operaciones.append(f"if ({cond}) {sentencia}" if cond else sentencia)
                    continue
                tipo_op, claves = next(iter(op.items()))
                if tipo_op == "todos":                   # la lista entera, con un dato List<objeto de valor>
                    asignaciones.append({"prop": vo["prop"], "expr": f"[.. ({amb.expr(claves, True)} ?? [])]"})
                    continue
                props = {c["nombre"]: c["prop"] for c in vo["campos"]}
                pred = " && ".join(f'e.{props[k]} == {amb.expr(k, True)}' for k in claves)
                if tipo_op == "quitar":                  # no falla si ya no estaba
                    operaciones.append(f"{lista}.RemoveAll(e => {pred});")
                else:                                    # reemplazar: 404 si no hay ninguno con esa clave
                    falta = cs_cadena(f'No hay un "{nombre_vo}" con ese {" y ".join(claves)}.')
                    operaciones.append(f"if ({lista}.RemoveAll(e => {pred}) == 0) throw new NoEncontrado({falta});")
                    operaciones.append(agregar(vo, lista, nuevo(vo)))
            elif isinstance(g, dict):                    # {campo de la raíz: dato}
                campo, dato = next(iter(g.items()))
                c = next(x for x in r["campos"] if x["nombre"] == campo)
                asignaciones.append({"prop": c["prop"], "expr": amb.expr(dato, tipos.interpretar(c["tipo_yaml"])["opcional"])})
            elif g in self.vos:
                vo = self.vos[g]
                asignaciones.append({"prop": vo["prop"], "expr": nuevo(vo)})
            else:
                c = next(x for x in r["campos"] if x["nombre"] == g)
                asignaciones.append({"prop": c["prop"], "expr": amb.expr(g, tipos.interpretar(c["tipo_yaml"])["opcional"])})
        return asignaciones, operaciones
