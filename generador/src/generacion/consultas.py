"""Consultas: por identidad o sobre todas las raíces."""
from __future__ import annotations

from comun import nombres
from generacion.csharp import Ambito, fuente, lineas, provisional
from validacion import valores


class Consultas:
    """Prepara las consultas del contexto."""

    def preparar_consultas(self):
        self.consultas = []
        for mq in self.ctx["consultas"]:
            self.preparar_consulta(mq)

    def preparar_consulta(self, mq: dict):
        sq = self.s["consultas"][mq["nombre"]]
        # La raíz de la consulta: la que dice "de" o la única que lee (G2). Las demás que lee van en datos.
        leidas = [self.usar_raiz(x["raiz_id"])["nombre"] for x in mq["lee"]]
        r = self.usar_raiz(sq.get("de") or leidas[0])
        otras = [self.raices[x]["raiz"] for x in dict.fromkeys(leidas) if x != r["nombre"]]
        clase = nombres.pascal(mq["nombre"])
        n = {k: self.tipo_cs_nuevo(x, f'consulta "{mq["nombre"]}"') for k, x in
             {"clase": clase, "salida": f"{clase}Salida", "datos": f"{clase}Datos", "manejador": f"{clase}Manejador"}.items()}
        ent = self.campos(sq.get("entrada"), f'entrada de "{mq["nombre"]}" (YAML)')
        todas = sq.get("sobre") == "todas"            # G5: sobre todas las raíces, sin identidad
        params = ([] if todas else [{"cs": "string", "prop": r["id_prop"]}]) + ent
        self.revisar_miembros(clase, [p["prop"] for p in params])
        amb = Ambito()
        if not todas and otras:                       # G5: las demás raíces que lee, por la misma identidad; pueden no existir
            capa_otras = {}
            for o in otras:
                for k_, f_ in self.raices[o["nombre"]]["fuentes"].items():
                    resto = f_["requerido"].removeprefix(o["var"] + ".")
                    if k_ != "estado" and resto != f_["requerido"] and "(" not in resto:
                        capa_otras.setdefault(k_, fuente(f'{o["var"]}?.{resto}', valores.opcional(f_["tipo"])))
            amb.agregar(capa_otras)
        amb.agregar(dict(self.fuentes_raiz))
        amb.agregar({c["nombre"]: fuente(f'consulta.{c["prop"]}', c["tipo"]) for c in ent})
        salida, filtro, elemento = [], [], None
        lista = todas and "agrega" not in sq          # sin agregaciones devuelve una lista (G5)
        if lista:
            ent_por_nombre = {c["nombre"]: c for c in ent}
            for dato in sq.get("filtro") or []:
                filtro.append(f'{self.fuentes_raiz[dato]["opcional"]} == consulta.{ent_por_nombre[dato]["prop"]}')
            elemento = self.tipo_cs_nuevo(f"{clase}Elemento", f'consulta "{mq["nombre"]}"')
            campos_el = [{**c, "expr": self.fuentes_raiz[c["nombre"]]["requerido"]}
                         for c in self.campos(sq.get("salida"), f'salida de "{mq["nombre"]}" (YAML)')]
            self.revisar_miembros(elemento, [c["prop"] for c in campos_el])
            prop_lista = nombres.pascal(sq["lista"])
            salida.append({"nombre": sq["lista"], "prop": prop_lista, "cs": f"List<{elemento}>",
                           "tipo": {"base": "lista", "lista": True, "opcional": False, "enum": None, "tipo": "lista"},
                           "expr": "elementos"})
        elif todas:
            # Filtro: igualdad entre el dato de la raíz y el de la entrada con el mismo nombre.
            ent_por_nombre = {c["nombre"]: c for c in ent}
            for dato in sq.get("filtro") or []:
                filtro.append(f'{self.fuentes_raiz[dato]["opcional"]} == consulta.{ent_por_nombre[dato]["prop"]}')
            for c in self.campos(sq.get("salida"), f'salida de "{mq["nombre"]}" (YAML)'):
                salida.append({**c, "expr": self.agregacion(sq["agrega"][c["nombre"]], c)})
        else:
            for c in self.campos(sq.get("salida"), f'salida de "{mq["nombre"]}" (YAML)'):
                salida.append({**c, "expr": amb.expr(c["nombre"], c["tipo"]["opcional"])})
        calculados = []
        for c in self.campos(sq.get("calculados"), f'calculados de "{mq["nombre"]}" (YAML)'):
            calculados.append({"nombre": c["nombre"], "metodo": c["prop"], "cs": c["cs"], "tipo_yaml": c["tipo"]["tipo"],
                               "provisional": provisional(c["tipo"])})
            salida.append({**c, "expr": f'{c["prop"]}(datos)'})
        self.revisar_miembros(n["salida"], [c["prop"] for c in salida])
        self.revisar_miembros(n["manejador"], [k["metodo"] for k in calculados])
        id_param = nombres.camel(r["id_nombre"])
        lambda_params = ([] if todas else [f"string {id_param}"]) + [f'{c["cs"]} {nombres.camel(c["nombre"])}' for c in ent]
        args = ([] if todas else [id_param]) + [nombres.camel(c["nombre"]) for c in ent]
        k = mq["contrato"]
        q = {**n, "nombre": mq["nombre"], "codigo": mq["codigo"], "id": mq["id"], "parametros": params,
             "salida_campos": salida, "calculados": calculados, "contrato": k, "servicio_negocio": mq["servicio_negocio"],
             "reglas": lineas(k["reglas"]) if k["reglas"] else ["El contrato no tiene reglas."],
             "salida_contrato": lineas(k["salida"]),
             "todas": todas, "filtro": " && ".join(filtro) or "true", "lista": lista, "elemento": elemento,
             "elemento_campos": campos_el if lista else [], "filtro_manual": bool(sq.get("filtro_manual")),
             "orden": [self.fuentes_raiz[x]["requerido"] for x in sq.get("orden") or []],
             "otras": otras, "raiz_nombre": r["nombre"],
             "ruta": f'{self.ruta_base}/consultas/{nombres.ruta(mq["nombre"])}' + ("" if todas else f"/{{{id_param}}}"),
             "ruta_prueba": f'/consultas/{nombres.ruta(mq["nombre"])}',
             "lambda_params": ", ".join(lambda_params), "args": ", ".join(args),
             "archivo": f'{self.proyecto}/Consultas/{clase}.g.cs', "manual": f'{self.proyecto}/Consultas/{clase}.cs',
             "entrada_campos": ent}
        self.consultas.append(q)
        cab = self.cabecera("ApplicationService", mq["nombre"], mq["id"], mq["codigo"])
        self.render("consulta.g.cs.j2", q["archivo"], q=q, raiz=r, cabecera=cab)
        self.render("consulta_manual.cs.j2", q["manual"], manual=True, q=q, raiz=r, cabecera=cab)
        for x in ("clase", "salida", "datos", "manejador"):
            self.traza_de(mq["id"], "ApplicationService", mq["nombre"], q["archivo"], n[x])
        self.traza_de(mq["id"], "ApplicationService", mq["nombre"], q["manual"], f'{n["manejador"]} (manual)')
        self.traza_de(mq["id"], "ApplicationService", mq["nombre"], f"{self.proyecto}/Registro.g.cs", f'GET {q["ruta"]}')
        for lee in mq["lee"]:
            leida = self.usar_raiz(lee["raiz_id"])["nombre"]
            self.traza_de(lee["acceso_id"], "Access", f'{mq["nombre"]} -> {leida} (lectura)', q["archivo"], n["manejador"])
        self.usar_raiz(r["nombre"])
        self.traza_de(mq["servicio_negocio"]["id"], "BusinessService", mq["servicio_negocio"]["nombre"], q["archivo"], n["manejador"])
        self.traza_de(k["id"], "Contract", k["nombre"], q["archivo"], n["manejador"])
        self.traza_de(k["id"], "Contract", k["nombre"], q["manual"], f'{n["manejador"]}.ValidarReglas (manual)')

    def agregacion(self, texto: str, salida: dict) -> str:
        """Expresión de C# de una agregación sobre "raices" (YAML: agrega), con el tipo de su dato de salida."""
        if texto == "conteo":
            return "raices.Count"
        funcion, dato = texto.split(" de ", 1)
        v = self.raiz["var"]
        e = self.fuentes_raiz[dato.strip()]["requerido"]
        if funcion == "suma":
            return f"raices.Sum({v} => {e})"
        metodo = {"promedio": "Average", "mínimo": "Min", "máximo": "Max"}[funcion]
        valor = f"({salida['cs']})raices.{metodo}({v} => (decimal){e})" if funcion == "promedio" \
            else f"({salida['cs']})raices.{metodo}({v} => {e})"
        return f"raices.Count == 0 ? null : {valor}"
