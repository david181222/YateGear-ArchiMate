"""Servicios de la capa anticorrupción: los que la aplicación llama, los que envían y los que reciben."""
from __future__ import annotations

from comun import nombres
from generacion.csharp import Ambito, cs_cadena, cs_literal, fuente
from validacion import valores


class ServiciosSA:
    """Prepara los servicios SA del contexto."""

    def preparar_sas(self):
        self.sas = {}
        for msa in self.ctx["servicios_sa"]:
            ssa = self.s["servicios_sa"][msa["nombre"]]
            if "entrada" not in ssa:                   # solo recibe (G7): ver preparar_mensajes_sa
                continue
            clase = nombres.pascal(msa["nombre"])
            ent = self.campos(ssa["entrada"], f'entrada de "{msa["nombre"]}" (YAML)')
            sal = self.campos(ssa["salida"], f'salida de "{msa["nombre"]}" (YAML)')
            nombres_cs = {k: self.tipo_cs_nuevo(v, f'servicio SA "{msa["nombre"]}"') for k, v in
                          {"interfaz": f"I{clase}", "entrada": f"{clase}Entrada", "salida": f"{clase}Salida",
                           "simulado": f"{clase}Simulado"}.items()}
            self.revisar_miembros(nombres_cs["entrada"], [c["prop"] for c in ent])
            self.revisar_miembros(nombres_cs["salida"], [c["prop"] for c in sal])
            tipos_ent = {c["nombre"]: c["tipo"] for c in ent}

            def respuesta(valores):
                return f'new {nombres_cs["salida"]}(' + ", ".join(cs_literal(valores.get(c["nombre"]), c["tipo"]) for c in sal) + ")"

            casos = []
            for caso in ssa.get("casos") or []:
                cond = " && ".join(
                    "(" + " || ".join(f'entrada.{nombres.pascal(k)} == {cs_literal(v, {**tipos_ent[k], "opcional": False})}' for v in vals) + ")"
                    for k, vals in caso["si"].items())
                casos.append({"condicion": cond, "respuesta": respuesta(caso["respuesta"])})
            con = msa["contraparte"]
            sa = {**nombres_cs, "nombre": msa["nombre"], "codigo": msa["codigo"], "id": msa["id"], "clase": clase,
                  "var": nombres.variable_local(msa["nombre"]), "entrada_campos": ent, "salida_campos": sal,
                  "casos": casos, "defecto": respuesta(ssa["respuesta_por_defecto"]),
                  "interfaz_modelo": msa["interfaz"], "contraparte": con, "flujos": msa["flujos"],
                  "contrato": msa["contrato"], "servicio_negocio": msa["servicio_negocio"],
                  "usa_casos": bool(casos), "spec": ssa}
            self.sas[msa["nombre"]] = sa
            archivo = f"{self.proyecto}/Anticorrupcion/{clase}.g.cs"
            self.render("servicio_sa.g.cs.j2", archivo, s=sa,
                        cabecera=self.cabecera("ApplicationService", msa["nombre"], msa["id"], msa["codigo"]))
            for k in ("interfaz", "simulado", "entrada", "salida"):
                self.traza_de(msa["id"], "ApplicationService", msa["nombre"], archivo, nombres_cs[k])
            self.traza_de(msa["interfaz"]["id"], "ApplicationInterface", msa["interfaz"]["nombre"], archivo, nombres_cs["interfaz"])
            self.traza_de(con["id"], con["tipo"], con["nombre"], archivo, nombres_cs["simulado"])
            for f in msa["flujos"]:
                self.traza_de(f["id"], "Flow", f'{f["nombre"]} ({f["direccion"]})', archivo, nombres_cs["simulado"])
            self.traza_de(msa["servicio_negocio"]["id"], "BusinessService", msa["servicio_negocio"]["nombre"], archivo, nombres_cs["interfaz"])
            self.traza_de(msa["contrato"]["id"], "Contract", msa["contrato"]["nombre"], archivo, nombres_cs["interfaz"])

    # ------------------------------------------------------------ mensajes que envían los SA (G11)
    def preparar_envios(self):
        """Lo que la aplicación envía por un SA que solo sale (YAML: envia): un mensaje por cada evento del contexto que lo
        dispara, con sus datos por nombre. El sistema externo está simulado: el envío queda en la bitácora."""
        self.emisores = []
        for msa in self.ctx["servicios_sa"]:
            envia = self.s["servicios_sa"][msa["nombre"]].get("envia") or {}
            if not envia:
                continue
            sa_clase = nombres.pascal(msa["nombre"])
            emisor = {k: self.tipo_cs_nuevo(v, f'servicio SA "{msa["nombre"]}"') for k, v in
                      {"interfaz": f"IEmisorDe{sa_clase}", "simulado": f"EmisorDe{sa_clase}Simulado"}.items()}
            mensajes = []
            for nombre in sorted(envia):
                x = envia[nombre]
                ev = self.eventos[x["cuando"]]
                clase = self.tipo_cs_nuevo(nombres.pascal(nombre), f'mensaje "{nombre}" de "{msa["nombre"]}"')
                datos = self.campos(x.get("datos"), f'datos de "{nombre}" (YAML)')
                self.revisar_miembros(clase, [d["prop"] for d in datos])
                amb = Ambito()
                amb.agregar(self.capa_evento(ev, "e"))
                args = [amb.expr(d["nombre"], d["tipo"]["opcional"]) for d in datos]
                mensajes.append({"nombre": nombre, "clase": clase, "datos": datos, "evento": ev["nombre"],
                                 "evento_clase": ev["clase"], "args": args, "titulo": f'{msa["nombre"]}: {nombre}'})
            archivo = f"{self.proyecto}/Anticorrupcion/EmisorDe{sa_clase}.g.cs"
            e = {**emisor, "sa": msa, "mensajes": mensajes, "var": "emisor" + sa_clase}
            self.emisores.append(e)
            self.render("emisor_sa.g.cs.j2", archivo, e=e, sa=msa,
                        cabecera=self.cabecera("ApplicationService", msa["nombre"], msa["id"], msa["codigo"]))
            for clase_cs in (emisor["interfaz"], emisor["simulado"]):
                self.traza_de(msa["id"], "ApplicationService", msa["nombre"], archivo, clase_cs)
            self.traza_de(msa["interfaz"]["id"], "ApplicationInterface", msa["interfaz"]["nombre"], archivo, emisor["interfaz"])
            con_m = msa["contraparte"]
            self.traza_de(con_m["id"], con_m["tipo"], con_m["nombre"], archivo, emisor["simulado"])
            for f in msa["flujos"]:
                self.traza_de(f["id"], "Flow", f'{f["nombre"]} ({f["direccion"]})', archivo, emisor["simulado"])
            self.traza_de(msa["servicio_negocio"]["id"], "BusinessService", msa["servicio_negocio"]["nombre"], archivo, emisor["interfaz"])
            self.traza_de(msa["contrato"]["id"], "Contract", msa["contrato"]["nombre"], archivo, emisor["interfaz"])
            for m_ in mensajes:
                self.traza_de(msa["id"], "ApplicationService", msa["nombre"], f"{self.proyecto}/Politicas/Politicas.g.cs",
                              f'envía "{m_["nombre"]}" con "{m_["evento"]}"')

    # ------------------------------------------------------------ mensajes que reciben los SA (G7)
    def preparar_mensajes_sa(self):
        """Lo que un sistema externo le envía a la aplicación por un SA (YAML: recibe). Por cada SA, un receptor con un
        método por mensaje: lee el JSON (revisa los datos obligatorios) y dispara el comando, por nombre de dato."""
        cmd_por_nombre = {c["nombre"]: c for c in self.comandos}
        self.receptores_sa, self.mensajes = [], []
        for msa in self.ctx["servicios_sa"]:
            recibe = self.s["servicios_sa"][msa["nombre"]].get("recibe") or {}
            if not recibe:
                continue
            sa_clase = nombres.pascal(msa["nombre"])
            receptor = self.tipo_cs_nuevo(f"ReceptorDe{sa_clase}", f'servicio SA "{msa["nombre"]}"')
            mensajes, manejadores = [], {}
            for nombre in sorted(recibe):
                x = recibe[nombre]
                lista = valores.disparos(x)                # uno o varios comandos, en orden (si uno falla, los demás no corren)
                cmd = cmd_por_nombre[lista[0][0]]
                self.usar_raiz(cmd["raiz_nombre"])
                clase = self.tipo_cs_nuevo(nombres.pascal(nombre), f'mensaje "{nombre}" de "{msa["nombre"]}"')
                datos = self.campos(x.get("datos"), f'datos de "{nombre}" (YAML)')
                self.revisar_miembros(clase, [d["prop"] for d in datos])
                amb = Ambito()
                amb.agregar({d["nombre"]: fuente(f'mensaje.{d["prop"]}', d["tipo"]) for d in datos})
                disparos_m = []
                for nombre_cmd, op in lista:
                    c_ = cmd_por_nombre[nombre_cmd]
                    rc = self.usar_raiz(c_["raiz_nombre"])
                    var_c = nombres.variable_local(c_["nombre"])
                    manejadores[var_c] = {"cs": c_["manejador"], "var": var_c}
                    disparos_m.append({"comando": c_["nombre"], "comando_clase": c_["clase"], "manejador_var": var_c,
                                       "args": ([] if c_["crea"] else [f'mensaje.{rc["id_prop"]}'])
                                       + self.argumentos(c_, amb, op.get("con") or {}, op.get("correspondencias") or {}),
                                       "condicion": self.condicion_disparo(op, amb, rc, f'mensaje.{rc["id_prop"]}', manejadores)})
                self.usar_raiz(cmd["raiz_nombre"])
                args, var_m = disparos_m[0]["args"], disparos_m[0]["manejador_var"]
                obligatorios = ", ".join(f"({cs_cadena(nombres.camel(d['nombre']))}, {cs_cadena(d['nombre'])})"
                                         for d in datos if not d["tipo"]["opcional"])
                m = {"nombre": nombre, "clase": clase, "datos": datos, "datos_campos": datos, "comando": cmd["nombre"],
                     "comandos": [d_["comando"] for d_ in disparos_m],
                     "disparos": disparos_m if not isinstance(x.get("dispara"), str) else None,
                     "comando_clase": cmd["clase"], "manejador_var": var_m, "args": args, "obligatorios": obligatorios,
                     "metodo": f"Recibir{clase}", "titulo": f'{msa["nombre"]}: {nombre}', "receptor": receptor,
                     "resumen": f'Mensaje "{nombre}" que recibe {msa["codigo"]} {msa["nombre"]}',
                     "descripcion": "Lo que el sistema externo le envía a la aplicación. Dispara: " + ", ".join(d_["comando"] for d_ in disparos_m) + ".",
                     "ruta": f'{self.ruta_base}/sa/{nombres.ruta(msa["nombre"])}/{nombres.ruta(nombre)}'}
                mensajes.append(m)
                self.mensajes.append(m)
            archivo = f"{self.proyecto}/Anticorrupcion/{receptor}.g.cs"
            self.render("receptor_sa.g.cs.j2", archivo, receptor=receptor, mensajes=mensajes, sa=msa,
                        manejadores=[manejadores[k] for k in sorted(manejadores)],
                        cabecera=self.cabecera("ApplicationService", msa["nombre"], msa["id"], msa["codigo"]))
            self.receptores_sa.append({"clase": receptor, "mensajes": mensajes})
            # Trazabilidad del SA, su interfaz, su contraparte y sus flujos (si solo recibe, no hay otro archivo).
            self.traza_de(msa["id"], "ApplicationService", msa["nombre"], archivo, receptor)
            self.traza_de(msa["interfaz"]["id"], "ApplicationInterface", msa["interfaz"]["nombre"], archivo, receptor)
            con_m = msa["contraparte"]
            self.traza_de(con_m["id"], con_m["tipo"], con_m["nombre"], archivo, receptor)
            for f in msa["flujos"]:
                self.traza_de(f["id"], "Flow", f'{f["nombre"]} ({f["direccion"]})', archivo, receptor)
            self.traza_de(msa["servicio_negocio"]["id"], "BusinessService", msa["servicio_negocio"]["nombre"], archivo, receptor)
            self.traza_de(msa["contrato"]["id"], "Contract", msa["contrato"]["nombre"], archivo, receptor)
            for m in mensajes:
                self.traza_de(msa["id"], "ApplicationService", msa["nombre"], f"{self.proyecto}/Registro.g.cs", f'POST {m["ruta"]}')
