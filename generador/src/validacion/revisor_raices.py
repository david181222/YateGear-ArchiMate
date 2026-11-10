"""Revisión de las raíces: identidad, estado y entidades."""
from __future__ import annotations

from comun import tipos


class RevisionDeRaices:
    """Revisa la sección raices del YAML."""

    def preparar_raiz(self, nombre_raiz: str, ag: dict, r_yaml) -> dict:
        """Identidad, estado y datos de una raíz. No cambia la raíz actual (ver usar)."""
        r = self.mapa(r_yaml, f"raices > {nombre_raiz}", ["identidad", "estado", "entidades"], ["identidad", "estado"])
        di = f"raices > {nombre_raiz} > identidad"
        ident = self.mapa(r.get("identidad"), di, ["nombre", "tipo", "prefijo", "digitos", "de"], ["nombre", "tipo"])
        id_nombre = ident.get("nombre", "")
        id_tipo = self.tipo(ident.get("tipo"), f"{di} > tipo")
        if id_tipo and (id_tipo["base"] != "string" or id_tipo["lista"] or id_tipo["opcional"]):
            self.error(di, "la identidad debe ser string obligatorio")
        campos_raiz = {c["nombre"]: c for c in ag["raiz"]["campos"]}
        # La identidad es un consecutivo (prefijo y digitos) o se forma con datos (de), una de las dos (G3).
        # Con un solo dato que se llama como la identidad, la identidad es recibida: llega con ese nombre.
        id_de, componentes, recibida = None, {}, False
        consecutivo = "prefijo" in ident or "digitos" in ident
        if consecutivo == ("de" in ident):
            self.error(di, "la identidad es un consecutivo (prefijo y digitos) o se forma con datos (de); una de las dos")
        elif consecutivo:
            if not isinstance(ident.get("prefijo"), str):
                self.error(di, "prefijo debe ser texto, por ejemplo ARR-")
            if not isinstance(ident.get("digitos"), int) or isinstance(ident.get("digitos"), bool) or ident.get("digitos", 0) < 1:
                self.error(di, "digitos debe ser un entero mayor que 0")
        else:
            de = self.mapa(ident.get("de"), f"{di} > de")
            if not de:
                self.error(f"{di} > de", "di con qué datos se forma la identidad, en orden")
            id_de = []
            recibida = list(de) == [id_nombre]
            for parte, texto in de.items():
                dp = f"{di} > de > {parte}"
                if parte == id_nombre and recibida:     # identidad recibida: su tipo es el de la identidad
                    id_de.append(parte)
                    continue
                if parte in (id_nombre, "estado"):
                    self.error(dp, "la identidad no se forma con la identidad (salvo si es su único dato) ni con el estado")
                    continue
                if texto is None:                         # campo de la raíz: su tipo sale del modelo
                    if parte not in campos_raiz:
                        self.error(dp, f'no es un campo de la raíz {nombre_raiz}; si no lo es, escribe su tipo')
                        continue
                    t_parte = tipos.interpretar(campos_raiz[parte]["tipo"])
                else:                                     # dato que no es campo: la raíz lo guarda como parte de su identidad
                    if parte in campos_raiz:
                        self.error(dp, "es un campo de la raíz: no lleva tipo (sale del modelo)")
                        continue
                    t_parte = self.tipo(texto, dp)
                    if not t_parte:
                        continue
                    componentes[parte] = t_parte
                if t_parte["lista"] or t_parte["opcional"] or t_parte["base"] not in ("string", "int", "enum", "DateOnly", "DateTime"):
                    self.error(dp, f'una parte de la identidad es string, int, enum, DateOnly o DateTime, obligatoria; aquí es {t_parte["tipo"]}')
                id_de.append(parte)
        # Entidades (G9): cada una dice cuál de sus campos es su identidad dentro de la raíz.
        ents_m = {e["nombre"]: e for e in ag["entidades"]}
        ents_y = self.mapa(r.get("entidades"), f"raices > {nombre_raiz} > entidades")
        self.cubre(f"raices > {nombre_raiz} > entidades", ents_y, ents_m, "entidad de la raíz")
        entidades = {}
        for n_e in sorted(set(ents_y) & set(ents_m)):
            de_e = f"raices > {nombre_raiz} > entidades > {n_e}"
            x_e = self.mapa(ents_y[n_e], de_e, ["identidad"], ["identidad"])
            campos_e = {c["nombre"]: c for c in ents_m[n_e]["campos"]}
            ide = x_e.get("identidad")
            if ide not in campos_e:
                self.error(f"{de_e} > identidad", f'"{ide}" no es un campo de la entidad; campos: {", ".join(campos_e)}')
                continue
            t_e = tipos.interpretar(campos_e[ide]["tipo"])
            if t_e["lista"] or t_e["opcional"] or t_e["base"] not in ("string", "int"):
                self.error(f"{de_e} > identidad", f'la identidad de una entidad es un campo string o int obligatorio; "{ide}" es {t_e["tipo"]}')
            if ents_m[n_e]["compuesto_por"] != ag["raiz"]["id"]:
                self.error(de_e, "solo se generan entidades que compone la raíz")
            entidades[n_e] = ide
        for v in ag["objetos_valor"]:
            if v["compuesto_por"] != ag["raiz"]["id"]:
                self.error(f"raices > {nombre_raiz}", f'"{v["nombre"]}" lo compone una entidad: todavía no se genera (G9)')
        estado_t = self.tipo(r.get("estado"), f"raices > {nombre_raiz} > estado")
        if estado_t and (estado_t["base"] != "enum" or estado_t["opcional"]):
            self.error(f"raices > {nombre_raiz} > estado", "el estado debe ser un enum obligatorio")
            estado_t = None

        # Campos de la raíz y de sus objetos de valor. Un nombre que está en dos de ellos es ambiguo:
        # solo es error si un comando, evento o consulta lo usa sin que llegue por su entrada o por un SA.
        vos = {v["nombre"]: v for v in ag["objetos_valor"] + ag["entidades"]}
        todos, origenes = {}, {}
        for dueno, lista in [(nombre_raiz, ag["raiz"]["campos"])] + [(v["nombre"], v["campos"]) for v in vos.values()]:
            for c in lista:
                if c["nombre"] in (id_nombre, "estado"):
                    self.error("modelo", f'el campo "{c["nombre"]}" de "{dueno}" se llama igual que la identidad o el estado')
                origenes.setdefault(c["nombre"], []).append(f'"{dueno}"')
                todos.setdefault(c["nombre"], c)
        for parte in componentes:
            if parte in todos:
                self.error(f"raices > {nombre_raiz} > identidad > de > {parte}", f"se llama igual que un campo de {origenes[parte][0]}")
        base = {**({id_nombre: id_tipo} if id_tipo else {}), **componentes}
        # Los campos de una lista (objeto de valor con Cardinalidad Muchos) no son datos sueltos de la raíz: no
        # están disponibles por su nombre, aunque sí se pueden fijar con valores al guardar en la lista.
        en_listas = {c["nombre"] for v in vos.values() if v["cardinalidad"] == "Muchos" for c in v["campos"]}
        sueltos = {k: c for k, c in todos.items() if k not in en_listas or k in campos_raiz}
        return {"nombre": nombre_raiz, "id": ag["raiz"]["id"], "agregado_id": ag["id"],
                "id_nombre": id_nombre, "id_tipo": id_tipo, "id_de": id_de, "componentes": componentes,
                "consecutivo": consecutivo, "recibida": recibida, "entidades": entidades,
                "estado_t": estado_t, "estados": estado_t["enum"]["valores"] if estado_t else [],
                "campos_raiz": campos_raiz, "vos": vos, "todos": todos,
                "ambiguos": {n: l for n, l in origenes.items() if len(l) > 1},
                "base": base, "con_raiz": {**base, **sueltos, **({"estado": estado_t} if estado_t else {})}}

    def usar(self, rc: dict):
        """Hace de rc la raíz actual (la usan pide, campos, condicion y estados_validos) y devuelve sus datos."""
        self.rc = rc
        self.id_nombre, self.id_tipo, self.estados = rc["id_nombre"], rc["id_tipo"], rc["estados"]
        self.ambiguos, self.componentes, self.id_de = rc["ambiguos"], rc["componentes"], rc["id_de"]
        return rc["con_raiz"], rc["todos"], rc["campos_raiz"], rc["vos"], rc["base"], rc["estado_t"], rc["nombre"]
