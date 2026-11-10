"""Revisión de los servicios SA: los que la aplicación llama, los que reciben y los que envían."""
from __future__ import annotations

from validacion.valores import disparos, mismo_tipo, valor_valido


class RevisionDeServiciosSA:
    """Revisa la sección servicios_sa del YAML."""

    def revisar_servicios_sa(self):
        """Los servicios SA van antes que los comandos, porque los comandos los usan."""
        s, ctx = self.s, self.ctx
        sas_m = {x["nombre"]: x for x in ctx["servicios_sa"]}
        sas_y = self.mapa(s.get("servicios_sa"), "servicios_sa")
        self.cubre("servicios_sa", sas_y, sas_m, "servicio SA")
        sas = self.sas = {}
        self.mensajes_crudos: dict[str, dict] = {}      # SA -> mensajes que recibe (G7), se revisan después de los comandos
        self.envios_crudos: dict[str, dict] = {}        # SA -> mensajes que envía (G11), se revisan con los eventos
        for n in sorted(set(sas_y) & set(sas_m)):
            d = f"servicios_sa > {n}"
            # Un SA que llama la aplicación (sale) declara entrada, salida y respuestas simuladas; uno que recibe lo que el
            # sistema externo le envía a la aplicación (G7) declara recibe. Puede tener las dos partes.
            x = self.mapa(sas_y[n], d, ["entrada", "salida", "respuesta_por_defecto", "casos", "recibe", "envia"],
                          [] if {"recibe", "envia"} & set(sas_y[n] or {}) else ["entrada", "salida", "respuesta_por_defecto"])
            sale = any(k in x for k in ("entrada", "salida", "respuesta_por_defecto"))
            if sale:
                for k in ("entrada", "salida", "respuesta_por_defecto"):
                    if k not in x:
                        self.error(d, f'falta la clave "{k}" (un SA que la aplicación llama declara entrada, salida y respuesta_por_defecto)')
            direcciones = {f["direccion"] for f in sas_m[n]["flujos"]}
            if "recibe" in x and "entra" not in direcciones:
                self.error(f"{d} > recibe", "en el modelo ningún flujo entra por la interfaz de este SA: no recibe nada")
            if "recibe" in x:
                self.mensajes_crudos[n] = self.mapa(x["recibe"], f"{d} > recibe")
            # G11: un SA al que la aplicación llama y espera respuesta necesita un flujo que entre; uno que solo sale
            # (lenguaje publicado) se declara con envia: sus mensajes salen con un evento del contexto.
            if sale and "entra" not in direcciones:
                self.error(d, "en el modelo ningún flujo entra por la interfaz de este SA: no responde. "
                              "Si la aplicación solo le envía datos, decláralo con envia")
            if "envia" in x:
                if "sale" not in direcciones:
                    self.error(f"{d} > envia", "en el modelo ningún flujo sale por la interfaz de este SA: no envía nada")
                self.envios_crudos[n] = self.mapa(x["envia"], f"{d} > envia")
            ent = self.campos(x.get("entrada"), f"{d} > entrada", libres=True)
            sal = self.campos(x.get("salida"), f"{d} > salida")

            def respuesta(resp, donde):
                resp = self.mapa(resp, donde)
                for k in sorted(set(sal) - set(resp)):
                    self.error(donde, f'falta el valor de "{k}"')
                for k, v in resp.items():
                    if k not in sal:
                        self.error(donde, f'"{k}" no está en la salida del servicio')
                    elif not valor_valido(v, sal[k]):
                        self.error(donde, f'el valor {v!r} no es válido para "{k}" ({sal[k]["tipo"]})')

            if sale:
                respuesta(x.get("respuesta_por_defecto"), f"{d} > respuesta_por_defecto")
            for i, caso in enumerate(self.lista(x.get("casos"), f"{d} > casos"), 1):
                caso = self.mapa(caso, f"{d} > casos {i}", ["si", "respuesta"], ["si", "respuesta"])
                self.condicion(caso.get("si"), ent, f"{d} > casos {i} > si")
                respuesta(caso.get("respuesta"), f"{d} > casos {i} > respuesta")
            sas[n] = {"entrada": ent, "salida": sal, "usado_por": ["envia"] if "envia" in x else [], "llamable": sale}

    def revisar_mensajes_sa(self):
        """Mensajes que reciben los SA: disparan un comando, como un evento de otro contexto, y pueden crear la raíz."""
        s, sas, entradas_cmd = self.s, self.sas, self.entradas_cmd
        self.mensajes_sa = {}
        for sa, mensajes in sorted(self.mensajes_crudos.items()):
            for msj, x in sorted(mensajes.items()):
                d = f"servicios_sa > {sa} > recibe > {msj}"
                x = self.mapa(x, d, ["dispara", "con", "correspondencias", "datos"], ["dispara", "datos"])
                if not isinstance(x.get("dispara"), str):
                    for k in ("con", "correspondencias"):
                        if k in x:
                            self.error(f"{d} > {k}", f"con varios comandos, {k} va en cada comando de dispara")
                if msj in entradas_cmd or msj in (s.get("consultas") or {}) or msj in (s.get("eventos_de_otros_contextos") or {}):
                    self.error(d, f'"{msj}" ya es el nombre de un comando, una consulta o un evento: los nombres no se repiten')
                # Puede disparar varios comandos (en orden; si uno falla, los siguientes no corren). Todos sus comandos
                # trabajan con raíces de la misma identidad.
                lista = disparos(x)
                if not lista:
                    self.error(f"{d} > dispara", "es un comando, una lista de comandos o {comando: {con, correspondencias, si, salvo}}")
                datos, usados, cmds = None, set(), []
                for cmd, op in lista:
                    if cmd not in entradas_cmd:
                        self.error(d, f'dispara "{cmd}", que no es un comando especificado del contexto')
                        continue
                    if entradas_cmd[cmd]["todas"]:
                        self.error(d, f'"{cmd}" es un comando sobre todas las raíces: un mensaje no lo dispara')
                        continue
                    rc = self.raices[entradas_cmd[cmd]["raiz"]]
                    if datos is None:
                        self.usar(rc)
                        datos = self.campos(x.get("datos"), f"{d} > datos", permitidos=(self.id_nombre,))
                    elif rc["id_nombre"] != self.id_nombre:
                        self.error(d, f'"{cmd}" trabaja con "{rc["id_nombre"]}" y el primer comando con "{self.id_nombre}": '
                                      "los comandos de un mensaje usan la misma identidad")
                        continue
                    no_crea = not entradas_cmd[cmd]["crea"]
                    if no_crea and self.id_nombre not in datos:
                        self.error(f"{d} > datos", f'dispara "{cmd}", que trabaja sobre una raíz existente: debe traer "{self.id_nombre}"')
                    aporta = {k: v for k, v in datos.items() if not (no_crea and k == self.id_nombre)}
                    usados |= self.revisar_disparo(cmd, op, aporta, datos, entradas_cmd, f"{d} > {cmd}", "el mensaje")
                    cmds.append(cmd)
                for k in sorted(set(datos or {}) - usados):
                    if k != self.id_nombre:
                        self.aviso(d, f'"{k}" no está en la entrada de ningún comando que dispara: no se usa')
                if sa in sas:
                    sas[sa]["usado_por"].append(f'recibe "{msj}"')
                if cmds:
                    self.mensajes_sa[msj] = {"sa": sa, "dispara": cmds[0], "comandos": cmds, "datos": datos or {}}
        for sa, info in sorted(sas.items()):
            if not info["usado_por"]:
                self.error("servicios_sa", f'ningún comando usa "{sa}" (V9-DEC-03)')

    def revisar_envios_sa(self):
        """Mensajes que envían los SA: salen cuando ocurre un evento del contexto, con sus datos por nombre."""
        s, entradas_cmd, datos_evento, llegan_con = self.s, self.entradas_cmd, self.datos_evento, self.llegan_con
        self.envios_sa = {}
        for sa, envios in sorted(self.envios_crudos.items()):
            for msj, x in sorted(envios.items()):
                d = f"servicios_sa > {sa} > envia > {msj}"
                x = self.mapa(x, d, ["cuando", "datos"], ["cuando", "datos"])
                ev = x.get("cuando")
                if ev not in datos_evento:
                    self.error(f"{d} > cuando", f'"{ev}" no es un evento especificado del contexto')
                    continue
                if msj in self.mensajes_sa or msj in entradas_cmd or msj in (s.get("consultas") or {}):
                    self.error(d, f'"{msj}" ya es el nombre de un mensaje, un comando o una consulta')
                llegan, _ = llegan_con(ev)
                datos = self.campos(x.get("datos"), f"{d} > datos", libres=True)
                for k, tk in datos.items():
                    if k not in llegan:
                        self.error(f"{d} > datos", f'"{k}" no lo trae "{ev}"')
                    elif not mismo_tipo(llegan[k], tk):
                        self.error(f"{d} > datos", f'"{k}" llega en "{ev}" como {llegan[k]["tipo"]} y aquí es {tk["tipo"]}')
                self.envios_sa[msj] = {"sa": sa, "cuando": ev, "datos": datos}
