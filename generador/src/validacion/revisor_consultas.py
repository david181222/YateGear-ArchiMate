"""Revisión de las consultas: por identidad o sobre todas las raíces."""
from __future__ import annotations

from validacion.valores import mismo_tipo, opcional


class RevisionDeConsultas:
    """Revisa la sección consultas del YAML."""

    def revisar_consultas(self):
        s, ctx = self.s, self.ctx
        qs_m = {q["nombre"]: q for q in ctx["consultas"]}
        qs_y = self.qs_y = self.mapa(s.get("consultas"), "consultas")
        self.cubre("consultas", qs_y, qs_m, "consulta")
        for n in sorted(set(qs_y) & set(qs_m)):
            d = f"consultas > {n}"
            q = self.mapa(qs_y[n], d, ["entrada", "sobre", "de", "filtro", "filtro_manual", "salida", "agrega", "lista",
                                       "orden", "calculados"], ["entrada"])
            if "salida" not in q and "calculados" not in q:
                self.error(d, "debe tener salida o calculados")
            # La raíz de la consulta: la única que lee, o la que dice "de" (sobre cuál recorre, si lee varias).
            leidas = [self.raiz_por_id[x["raiz_id"]]["nombre"] for x in qs_m[n]["lee"] if x["raiz_id"] in self.raiz_por_id]
            if "de" in q:
                if "sobre" not in q and len(leidas) < 2:
                    self.error(f"{d} > de", "de va con sobre: todas o en una consulta que lee varias raíces")
                if q["de"] not in leidas:
                    self.error(f"{d} > de", f'"{q["de"]}" no es una raíz que la consulta lea en el modelo; lee: {", ".join(leidas)}')
                    continue
                nombre_q = q["de"]
            elif len(leidas) == 1:
                nombre_q = leidas[0]
            else:
                self.error(d, f'lee {len(leidas)} raíces ({", ".join(leidas)}): di con "de" cuál recorre (sobre: todas) '
                              "o por la identidad de cuál consulta")
                continue
            con_raiz, todos, *_ = self.usar(self.raices[nombre_q])
            if "sobre" in q:
                self.revisar_consulta_sobre_todas(q, d, con_raiz)
                continue
            for k in ("filtro", "filtro_manual", "agrega", "lista", "orden"):
                if k in q:
                    self.error(d, f"{k} solo va con sobre: todas")
            bolsa = dict(con_raiz)
            # G5: las demás raíces que lee se cargan con la misma identidad; sus datos llegan opcionales (si esa raíz
            # no existe, vacíos), y uno que se llama como uno de la raíz de la consulta no se toma.
            for otra in dict.fromkeys(leidas):
                if otra == nombre_q:
                    continue
                ro = self.raices[otra]
                if ro["id_nombre"] != self.id_nombre:
                    self.error(d, f'lee "{otra}", que se identifica con "{ro["id_nombre"]}", y la consulta va por "{self.id_nombre}": '
                                  "las raíces de una consulta por identidad tienen la misma identidad")
                    continue
                for k, tk in ro["con_raiz"].items():
                    if k not in bolsa and k != "estado":
                        bolsa[k] = opcional(tk)
            ent_q = self.campos(q.get("entrada"), f"{d} > entrada")
            self.agregar(bolsa, ent_q, f"{d} > entrada")
            for k in sorted(set(ent_q) & set(todos)):
                self.varios_origenes.append(f'{n}: "{k}" llega de raíz, entrada; se usa entrada')
            sal = self.campos(q.get("salida"), f"{d} > salida", libres=True)
            self.pide(bolsa, sal, f"{d} > salida", "la consulta")
            for k in self.campos(q.get("calculados"), f"{d} > calculados"):
                if k in bolsa:
                    self.error(f"{d} > calculados", f'"{k}" ya está disponible: va en salida')

    AGREGACIONES = ("promedio", "suma", "mínimo", "máximo")

    def interpretar_agregado(self, texto, con_raiz: dict, donde: str):
        """ "conteo" o "<promedio|suma|mínimo|máximo> de <dato de la raíz>". Devuelve (función, dato o None)."""
        if texto == "conteo":
            return "conteo", None
        if isinstance(texto, str):
            for f in self.AGREGACIONES:
                if texto.startswith(f + " de "):
                    dato = texto[len(f) + 4:].strip()
                    if dato not in con_raiz:
                        self.error(donde, f'"{dato}" no es un dato de la raíz')
                        return None
                    return f, dato
        self.error(donde, f'{texto!r} no es una agregación; se escribe "conteo" o "<{"|".join(self.AGREGACIONES)}> de <dato>"')
        return None

    def revisar_consulta_sobre_todas(self, q: dict, d: str, con_raiz: dict):
        """Consulta sobre todas las instancias de la raíz (G5): filtra por igualdad con datos de su entrada y
        devuelve agregaciones (conteo, promedio, suma, mínimo, máximo)."""
        if q.get("sobre") != "todas":
            self.error(f"{d} > sobre", 'por ahora solo se permite "sobre: todas"')
            return
        ent = self.campos(q.get("entrada"), f"{d} > entrada")
        for dato in self.lista(q.get("filtro"), f"{d} > filtro"):
            if dato not in ent:
                self.error(f"{d} > filtro", f'"{dato}" no está en la entrada de la consulta')
            elif dato not in con_raiz:
                self.error(f"{d} > filtro", f'"{dato}" no es un dato de la raíz: no hay con qué compararlo')
            elif not mismo_tipo(ent[dato], con_raiz[dato]):
                self.error(f"{d} > filtro", f'"{dato}" llega como {ent[dato]["tipo"]} y en la raíz es {con_raiz[dato]["tipo"]}')
        if q.get("filtro_manual", False) not in (True, False):
            self.error(f"{d} > filtro_manual", "es true o false")
        sal = self.campos(q.get("salida"), f"{d} > salida", libres=True)
        if "agrega" not in q:
            # Sin agregaciones, la consulta devuelve una lista: un elemento por raíz, con los datos de la salida.
            if not isinstance(q.get("lista"), str) or not q["lista"].strip():
                self.error(d, "sin agrega, la consulta devuelve una lista: di su nombre con lista (por ejemplo, lista: elementos disponibles)")
            self.pide(con_raiz, sal, f"{d} > salida", "un elemento de la lista")
            for dato in self.lista(q.get("orden"), f"{d} > orden"):      # de menor a mayor, en el orden escrito
                if dato not in con_raiz or con_raiz[dato]["lista"]:
                    self.error(f"{d} > orden", f'"{dato}" no es un dato de la raíz (que no sea una lista) por el que se pueda ordenar')
            return
        for k in ("lista", "orden"):
            if k in q:
                self.error(f"{d} > {k}", "con agrega la consulta devuelve agregaciones, no una lista")
        agrega = self.mapa(q.get("agrega"), f"{d} > agrega")
        for k in sorted(set(sal) - set(agrega)):
            self.error(f"{d} > agrega", f'falta cómo se calcula "{k}": en una consulta sobre todas, cada dato de la salida es una agregación')
        for k in sorted(set(agrega) - set(sal)):
            self.error(f"{d} > agrega", f'"{k}" no está en la salida')
        for k in sorted(set(sal) & set(agrega)):
            res = self.interpretar_agregado(agrega[k], con_raiz, f"{d} > agrega > {k}")
            if not res:
                continue
            f, dato = res
            ts = sal[k]
            if f == "conteo":
                if ts["base"] != "int" or ts["lista"]:
                    self.error(f"{d} > salida > {k}", "un conteo es int")
                continue
            tc = con_raiz[dato]
            if tc["lista"] or tc["opcional"]:
                self.error(f"{d} > agrega > {k}", f'"{dato}" debe ser un dato obligatorio y no una lista')
            elif f in ("promedio", "suma") and tc["base"] not in ("int", "decimal"):
                self.error(f"{d} > agrega > {k}", f'el {f} es de números; "{dato}" es {tc["tipo"]}')
            elif f in ("mínimo", "máximo") and tc["base"] not in ("int", "decimal", "DateOnly", "DateTime"):
                self.error(f"{d} > agrega > {k}", f'el {f} es de números o fechas; "{dato}" es {tc["tipo"]}')
            esperado = "decimal" if f == "promedio" else tc["base"]
            if ts["base"] != esperado or ts["lista"]:
                self.error(f"{d} > salida > {k}", f"el {f} de \"{dato}\" es {esperado}")
            if f != "suma" and not ts["opcional"]:
                self.error(f"{d} > salida > {k}", f"sin instancias no hay {f}: escribe {esperado}?")
