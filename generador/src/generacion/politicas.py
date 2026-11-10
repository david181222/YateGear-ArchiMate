"""Políticas internas: un evento del contexto dispara un comando del mismo contexto."""
from __future__ import annotations

from comun import nombres
from generacion.csharp import Ambito, cs_cadena, cs_literal


class Politicas:
    """Prepara las políticas internas del contexto."""

    def preparar_politicas(self):
        """Políticas internas (YAML: politicas, G10 y D7). Sin entrada, cada evento dispara el comando por su cuenta; con
        si o salvo, solo si se cumple; con junto_con y uno_de, el comando corre cuando llegaron todos los de junto_con y
        uno de los de uno_de para la misma identidad (EsperaDeEventos), con los datos de los que llegaron."""
        ev_por_id = {e["id"]: e["nombre"] for e in self.ctx["eventos"]}
        cmd_por_id = {c["id"]: c for c in self.comandos}
        pol_y = self.s.get("politicas") or {}
        self.politicas, self.grupos = [], []
        grupos = {}
        for p in self.ctx["politicas"]:
            ev = self.eventos[ev_por_id[p["evento_id"]]]
            r = self.usar_raiz(ev["raiz"])
            cmd = cmd_por_id[p["comando_id"]]
            x = pol_y.get(cmd["nombre"]) or {}
            self.traza_de(p["relacion_id"], "Triggering", f'{ev["nombre"]} -> {cmd["nombre"]}',
                          f"{self.proyecto}/Politicas/Politicas.g.cs", "Politicas")
            if x.get("junto_con") or x.get("uno_de"):
                grupos.setdefault(cmd["nombre"], []).append((p, ev))
                continue
            amb = Ambito()
            amb.agregar(self.capa_evento(ev, "e"))
            args = [] if cmd["crea"] else [f'e.{r["id_prop"]}']
            args += self.argumentos(cmd, amb, x.get("con") or {}, x.get("correspondencias") or {})
            self.politicas.append({"relacion_id": p["relacion_id"], "evento": ev["nombre"], "evento_clase": ev["clase"],
                                   "comando": cmd["nombre"], "comando_clase": cmd["clase"],
                                   "manejador": cmd["manejador"], "args": args, "condicion": self.condicion(x, amb)})
        for nombre_cmd, rels in sorted(grupos.items()):
            cmd = next(c for c in self.comandos if c["nombre"] == nombre_cmd)
            x = pol_y[nombre_cmd]
            junto = list(x.get("junto_con") or [])
            uno_y = x.get("uno_de") or {}
            uno = {k: (v or {}) for k, v in uno_y.items()} if isinstance(uno_y, dict) else {k: {} for k in uno_y}
            evs = {ev["nombre"]: ev for _, ev in rels}
            variables = [{"var": nombres.variable_local(n), "clase": evs[n]["clase"], "nombre": cs_cadena(n), "seguro": n in junto}
                         for n in junto + list(uno)]
            amb = Ambito()
            for n in junto:
                amb.agregar(self.capa_evento(evs[n], nombres.variable_local(n)))
            con, corr = x.get("con") or {}, x.get("correspondencias") or {}
            args = [] if cmd["crea"] else ["e.Identidad"]
            for c in cmd["entrada_campos"]:
                dato = corr.get(c["nombre"], c["nombre"])
                if c["nombre"] in con:
                    args.append(cs_literal(con[c["nombre"]], c["tipo"]))
                elif amb.buscar(dato):                     # lo trae un evento de junto_con
                    args.append(amb.expr(dato, c["tipo"]["opcional"]))
                else:                                      # de uno de los de uno_de: el que llegó
                    expr = "null" if c["tipo"]["opcional"] else f'throw new DatoFaltante({cs_cadena(c["nombre"])})'
                    alguno = False
                    for n in reversed(list(uno)):
                        var = nombres.variable_local(n)
                        con_n = (uno[n].get("con") or {})
                        props = {d["nombre"]: d for d in evs[n]["datos"] + evs[n]["calculados"]}
                        if c["nombre"] in con_n:
                            expr, alguno = f'({var} is not null ? {cs_literal(con_n[c["nombre"]], c["tipo"])} : {expr})', True
                        elif dato in props:
                            expr, alguno = f'({var}?.{props[dato]["prop"]} ?? {expr})', True
                    args.append(expr if alguno else "null")
            self.grupos.append({"comando": cmd["nombre"], "comando_clase": cmd["clase"], "manejador": cmd["manejador"],
                                "metodo": f'{cmd["clase"]}PorVariosEventos', "grupo": cs_cadena(f'política: {cmd["nombre"]}'),
                                "junto": [cs_cadena(n) for n in junto], "uno": [cs_cadena(n) for n in uno],
                                "variables": variables, "args": args,
                                "relaciones": [{"relacion_id": p["relacion_id"], "evento": ev["nombre"], "evento_clase": ev["clase"]}
                                               for p, ev in sorted(rels, key=lambda pe: pe[0]["relacion_id"])]})

    def argumentos(self, cmd: dict, amb: Ambito, con: dict, corr: dict) -> list[str]:
        """Los datos de la entrada de un comando (sin su identidad): un valor fijo de con, o el dato con su nombre (o el
        de su correspondencia) que da amb; si no está, null."""
        args = []
        for c in cmd["entrada_campos"]:
            dato = corr.get(c["nombre"], c["nombre"])
            if c["nombre"] in con:
                args.append(cs_literal(con[c["nombre"]], c["tipo"]))
            elif amb.buscar(dato) is None:
                args.append("null")
            else:
                f = amb.buscar(dato)
                e = f["opcional"] if c["tipo"]["opcional"] else f["requerido"]
                if f["tipo"]["opcional"] and not c["tipo"]["opcional"]:
                    e = f'({e} ?? throw new DatoFaltante({cs_cadena(c["nombre"])}))'
                args.append(e)
        return args
