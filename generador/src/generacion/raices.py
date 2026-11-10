"""Raíces, entidades y objetos de valor de un contexto."""
from __future__ import annotations

from comun import nombres, tipos
from generacion.csharp import cs_cadena, cs_tipo, ErrorDeGeneracion, fuente


class Raices:
    """Prepara cada raíz del contexto, con sus entidades y objetos de valor."""

    def preparar_raiz(self):
        """Prepara cada raíz del contexto (una por agregado, G2). Cada comando, evento, consulta y paso de
        escenario trabaja con la de su agregado: ver usar_raiz."""
        self.raices = {}
        for ag in sorted(self.ctx["agregados"], key=lambda a: a["raiz"]["nombre"]):
            self.preparar_una_raiz(ag)
        self.usar_raiz(next(iter(self.raices)))

    def usar_raiz(self, clave: str) -> dict:
        """Hace de una raíz la actual (por su nombre, su ID o el ID de su agregado) y la devuelve."""
        x = self.raices.get(clave) or next((v for v in self.raices.values()
                                            if clave in (v["raiz"]["id"], v["raiz"]["agregado"]["id"])), None)
        if x is None:
            raise ErrorDeGeneracion(f'no hay una raíz "{clave}" en el contexto')
        self.raiz, self.fuentes_raiz, self.tipos_raiz, self.vos = x["raiz"], x["fuentes"], x["tipos"], x["vos"]
        return self.raiz

    def preparar_una_raiz(self, ag: dict):
        r = ag["raiz"]
        sr = self.s["raices"][r["nombre"]]
        ident = sr["identidad"]
        clase = self.tipo_cs_nuevo(nombres.pascal(r["nombre"]), f'raíz "{r["nombre"]}"')
        estado_t = self.tipo(sr["estado"], f'estado de la raíz "{r["nombre"]}" (YAML)')
        var = nombres.variable_local(r["nombre"])
        # Identidad: un consecutivo (prefijo y digitos) o formada con datos (de), G3.
        de = ident.get("de") or {}
        raiz = {"id": r["id"], "nombre": r["nombre"], "clase": clase, "var": var, "agregado": ag,
                "id_nombre": ident["nombre"], "id_prop": nombres.pascal(ident["nombre"]),
                "consecutivo": "de" not in ident, "prefijo": ident.get("prefijo"), "digitos": ident.get("digitos"),
                "id_de": list(de), "componentes": [], "recibida": list(de) == [ident["nombre"]],
                "repositorio": "repositorio" + clase,
                "estado_t": estado_t, "estado_clase": cs_tipo(estado_t), "campos": [], "vos": []}
        fuentes = {ident["nombre"]: fuente(f'{var}.{raiz["id_prop"]}', {**tipos.interpretar("string")}),
                   "estado": fuente(f"{var}.Estado", estado_t)}
        for parte, texto in de.items():           # las partes que no son campos: la raíz las guarda
            if texto is not None and parte != ident["nombre"]:
                t = self.tipo(texto, f'identidad de "{r["nombre"]}" (YAML)')
                comp = {"nombre": parte, "prop": nombres.pascal(parte), "tipo": t, "cs": cs_tipo(t)}
                raiz["componentes"].append(comp)
                fuentes[parte] = fuente(f'{var}.{comp["prop"]}', t)
        for c in r["campos"]:
            t = self.tipo(c["tipo"], f'campo "{c["nombre"]}" de "{r["nombre"]}" ({r["id"]})')
            prop = nombres.pascal(c["nombre"])
            if t["opcional"]:
                decl = f"{cs_tipo(t)} {prop} {{ get; set; }}"
            elif t["lista"]:
                decl = f"{cs_tipo(t)} {prop} {{ get; set; }} = [];"
            else:
                decl = f"required {cs_tipo(t)} {prop} {{ get; set; }}"
            raiz["campos"].append({"nombre": c["nombre"], "prop": prop, "tipo_yaml": c["tipo"], "decl": decl})
            fuentes[c["nombre"]] = fuente(f"{var}.{prop}", t)
        vos_raiz = {}
        # Las entidades (G9) se guardan en la raíz igual que un objeto de valor, pero con su identidad: la raíz no
        # admite dos con la misma (Entidades.Agregar).
        entidades_y = sr.get("entidades") or {}
        for v in ag["entidades"] + ag["objetos_valor"]:
            es_entidad = v in ag["entidades"]
            vclase = self.tipo_cs_nuevo(nombres.pascal(v["nombre"]),
                                        f'{"entidad" if es_entidad else "objeto de valor"} "{v["nombre"]}"')
            campos = []
            for c in v["campos"]:
                t = self.tipo(c["tipo"], f'campo "{c["nombre"]}" de "{v["nombre"]}" ({v["id"]})')
                campos.append({"nombre": c["nombre"], "prop": nombres.pascal(c["nombre"]), "tipo": t,
                               "cs": cs_tipo(t), "tipo_yaml": c["tipo"]})
            self.revisar_miembros(vclase, [c["prop"] for c in campos])
            card = v["cardinalidad"]
            prop = vclase
            if card == "Uno":
                decl = f"required {vclase} {prop} {{ get; set; }}"
            elif card == "Cero o uno":
                decl = f"{vclase}? {prop} {{ get; set; }}"
            else:
                decl = f"List<{vclase}> {prop} {{ get; set; }} = [];"
            vo = {"id": v["id"], "nombre": v["nombre"], "clase": vclase, "prop": prop, "card": card,
                  "comp_id": v["composicion_id"], "campos": campos, "decl": decl, "entidad": es_entidad}
            if es_entidad:
                ident_e = entidades_y[v["nombre"]]["identidad"]
                c_id = next(c for c in campos if c["nombre"] == ident_e)
                vo.update({"identidad": ident_e, "identidad_expr": c_id["prop"] if c_id["tipo"]["base"] == "string"
                           else f'{c_id["prop"]}.ToString(System.Globalization.CultureInfo.InvariantCulture)'})
            raiz["vos"].append(vo)
            vos_raiz[v["nombre"]] = vo
            for c in campos:
                if card == "Uno":
                    fuentes.setdefault(c["nombre"], fuente(f"{var}.{prop}.{c['prop']}", c["tipo"]))
                elif card == "Cero o uno":       # si se pide obligatorio y no hay objeto de valor, DatoFaltante
                    fuentes.setdefault(c["nombre"], fuente(
                        f'({var}.{prop} ?? throw new DatoFaltante({cs_cadena(v["nombre"])})).{c["prop"]}', c["tipo"],
                        f"{var}.{prop}?.{c['prop']}"))
        self.revisar_miembros(clase, [raiz["id_prop"], "Estado"] + [c["prop"] for c in raiz["componentes"]]
                              + [c["prop"] for c in raiz["campos"]] + [v["prop"] for v in raiz["vos"]])
        # Tipo de cada dato de la raíz por su nombre (para valores fijos de los comandos), incluidos los de sus
        # objetos de valor con Cardinalidad Muchos, que no son fuentes de la raíz.
        tipos_raiz = {k: f["tipo"] for k, f in fuentes.items()}
        for vo in raiz["vos"]:
            for c in vo["campos"]:
                tipos_raiz.setdefault(c["nombre"], c["tipo"])
        self.raices[r["nombre"]] = {"raiz": raiz, "fuentes": fuentes, "tipos": tipos_raiz, "vos": vos_raiz}

        dom = f"{self.proyecto}/Dominio"
        self.render("raiz.g.cs.j2", f"{dom}/{clase}.g.cs", r=raiz,
                    cabecera=self.cabecera("DataObject", r["nombre"], r["id"]))
        self.traza_de(ag["id"], "Grouping", ag["nombre"], f"{dom}/{clase}.g.cs", clase)
        self.traza_de(r["id"], "DataObject", r["nombre"], f"{dom}/{clase}.g.cs", clase)
        for vo in raiz["vos"]:
            self.render("entidad.g.cs.j2" if vo["entidad"] else "objeto_valor.g.cs.j2", f"{dom}/{vo['clase']}.g.cs", v=vo,
                        raiz=raiz, cabecera=self.cabecera("DataObject", vo["nombre"], vo["id"]))
            self.traza_de(vo["id"], "DataObject", vo["nombre"], f"{dom}/{vo['clase']}.g.cs", vo["clase"])
            self.traza_de(vo["comp_id"], "Composition", f'{r["nombre"]} -> {vo["nombre"]}',
                          f"{dom}/{clase}.g.cs", f'{clase}.{vo["prop"]}')
        for obj in [r] + ag["entidades"] + ag["objetos_valor"]:
            for c in obj["campos"]:
                if c["enum"]:
                    self.traza_de(obj["id"], "DataObject", f'{obj["nombre"]} (campo "{c["nombre"]}")',
                                  f"{dom}/Enums.g.cs", nombres.pascal(c["enum"]["nombre"]))
