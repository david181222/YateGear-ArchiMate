"""Eventos del contexto y eventos de otros contextos."""
from __future__ import annotations

from comun import nombres, tipos
from generacion.csharp import Ambito, cs_cadena, cs_literal, fuente
from validacion import valores


class Eventos:
    """Prepara los eventos que publica el contexto y los que recibe de otros."""

    def preparar_eventos(self):
        self.eventos = {}
        publica = {}
        for c in self.ctx["comandos"]:
            for e in c["eventos"]:
                publica.setdefault(e, []).append(f'"{c["nombre"]}" ({c["codigo"]})')
        for me in self.ctx["eventos"]:
            r = self.usar_raiz(me["agregado_id"])      # el evento lleva la identidad de la raíz de su agregado
            se = self.s["eventos"][me["nombre"]]
            clase = self.tipo_cs_nuevo(nombres.pascal(me["nombre"]), f'evento "{me["nombre"]}"')
            datos = self.campos(se.get("datos"), f'datos del evento "{me["nombre"]}" (YAML)')
            calc = self.campos(se.get("calculados"), f'calculados del evento "{me["nombre"]}" (YAML)')
            params = [{"cs": "string", "prop": r["id_prop"]}] + datos + calc
            self.revisar_miembros(clase, [p["prop"] for p in params] + ["NombreEnElModelo", "Identidad"])
            ev = {"id": me["id"], "nombre": me["nombre"], "clase": clase, "datos": datos, "calculados": calc,
                  "parametros": params, "publicado_por": ", ".join(publica.get(me["id"], [])), "raiz": r["nombre"]}
            self.eventos[me["nombre"]] = ev
            archivo = f"{self.proyecto}/Eventos/{clase}.g.cs"
            self.render("evento.g.cs.j2", archivo, e=ev, raiz=r,
                        cabecera=self.cabecera("ApplicationEvent", me["nombre"], me["id"]))
            self.traza_de(me["id"], "ApplicationEvent", me["nombre"], archivo, clase)

    def capa_evento(self, ev: dict, var: str, nulable: bool = False) -> dict:
        """Los datos de un evento del contexto por su nombre (con su identidad), leídos de la variable var."""
        r = self.raices[ev["raiz"]]["raiz"]
        capa = {r["id_nombre"]: fuente(f'{var}{"?" if nulable else ""}.{r["id_prop"]}', tipos.interpretar("string?" if nulable else "string"))}
        for d in ev["datos"] + ev["calculados"]:
            capa[d["nombre"]] = fuente(f'{var}{"?" if nulable else ""}.{d["prop"]}', valores.opcional(d["tipo"]) if nulable else d["tipo"])
        return capa

    # ------------------------------------------------------------ eventos de otros contextos (capa 3)
    def preparar_eventos_externos(self):
        catalogo = {(o["nombre"], e["nombre"]): e["id"] for o in self.ctx["otros_contextos"] for e in o["eventos"]}
        cmd_por_nombre = {c["nombre"]: c for c in self.comandos}
        ext = self.s.get("eventos_de_otros_contextos") or {}
        clases = {n: nombres.pascal(n) for n in ext}
        requeridos = {e for c in self.comandos for e in (c["spec"].get("requiere") or [])}
        self.externos, manejadores = [], {}
        for nombre in sorted(ext):
            se = ext[nombre]
            # La raíz del evento: la del (primer) comando que dispara (G2). Sin dispara, la identidad se escribe en el YAML.
            lista = valores.disparos(se)
            r = self.usar_raiz(cmd_por_nombre[lista[0][0]]["raiz_nombre"]) if lista else self.raiz
            clase = self.tipo_cs_nuevo(clases[nombre], f'evento de otro contexto "{nombre}"')
            datos = self.campos(se.get("datos"), f'datos de "{nombre}" (YAML)')
            # El evento llega con su identidad (YAML: identidad; por defecto, la de la raíz de este contexto).
            id_nombre = se.get("identidad") or r["id_nombre"]
            id_prop = nombres.pascal(id_nombre)
            params = [{"cs": "string", "prop": id_prop}] + datos
            self.revisar_miembros(clase, [p["prop"] for p in params] + ["NombreEnElModelo", "Identidad"])
            # Datos que deben venir en el JSON (D1): la identidad y los que no son opcionales. Si falta uno, DatoFaltante.
            obligatorios = [(nombres.camel(id_nombre), id_nombre)] + [
                (nombres.camel(d["nombre"]), d["nombre"]) for d in datos if not d["tipo"]["opcional"]]
            x = {"nombre": nombre, "clase": clase, "id": catalogo[(se["de"], nombre)], "de": se["de"],
                 "id_nombre": id_nombre, "id_prop": id_prop, "id_json": nombres.camel(id_nombre), "parametros": params,
                 "recordar": nombre in requeridos, "comando": None, "grupo": [], "junto_con": [], "disparos": None,
                 "ruta": f'{self.ruta_base}/eventos-externos/{nombres.ruta(nombre)}', "datos_campos": datos,
                 "obligatorios": ", ".join(f"({cs_cadena(p)}, {cs_cadena(n)})" for p, n in obligatorios)}
            if "dispara" not in se:                    # solo se recuerda, para los comandos que lo requieren
                self.registrar_externo(x)
                continue
            if not isinstance(se["dispara"], str):      # varios comandos, cada uno con sus opciones, en orden
                capa = {id_nombre: fuente(f"evento.{id_prop}", tipos.interpretar("string"))}
                capa.update({d["nombre"]: fuente(f'evento.{d["prop"]}', d["tipo"]) for d in datos})
                amb = Ambito()
                amb.agregar(capa)
                disparos_x = []
                for nombre_cmd, op in lista:
                    cmd = cmd_por_nombre[nombre_cmd]
                    rc = self.usar_raiz(cmd["raiz_nombre"])
                    id_raiz = f"evento.{id_prop}" if id_nombre == rc["id_nombre"] else f'evento.{rc["id_prop"]}'
                    var_m = nombres.camel(cmd["nombre"])
                    manejadores[var_m] = {"cs": cmd["manejador"], "var": var_m}
                    disparos_x.append({"comando": cmd["nombre"], "comando_clase": cmd["clase"], "manejador_var": var_m,
                                       "args": [id_raiz] + self.argumentos(cmd, amb, op.get("con") or {}, op.get("correspondencias") or {}),
                                       "condicion": self.condicion_disparo(op, amb, rc, id_raiz, manejadores)})
                self.usar_raiz(r["nombre"])
                x.update({"comando": disparos_x[0]["comando"], "disparos": disparos_x})
                self.registrar_externo(x)
                continue
            cmd = cmd_por_nombre[se["dispara"]]
            # Con junto_con, el comando corre con el último que llega: las correspondencias valen para todo el grupo.
            corr = {}
            for g in sorted(se.get("junto_con") or []):
                corr.update(ext[g].get("correspondencias") or {})
            corr.update(se.get("correspondencias") or {})
            junto = list(se.get("junto_con") or [])
            grupo = sorted([nombre] + junto)
            # De dónde sale cada dato de la entrada del comando: con (fijo) o un evento del grupo, por nombre.
            variables = [{"var": nombres.camel(g), "clase": clases[g], "nombre": cs_cadena(g)} for g in grupo] if junto else []
            fuentes_ev = [(nombres.camel(g) if junto else "evento", {k: tipos.interpretar(t) for k, t in (ext[g].get("datos") or {}).items()})
                          for g in (grupo if junto else [nombre])]
            con = se.get("con") or {}
            # La identidad de la raíz: la del evento, o (si llega con otra, G3) el dato de la raíz por su nombre.
            id_raiz = f'evento.{id_prop}' if id_nombre == r["id_nombre"] else f'evento.{r["id_prop"]}'
            args = [id_raiz]
            fuentes_ev = [(var, {**d, id_nombre: tipos.interpretar("string")}) for var, d in fuentes_ev]
            for c in cmd["entrada_campos"]:
                if c["nombre"] in con:
                    args.append(cs_literal(con[c["nombre"]], c["tipo"]))
                    continue
                dato = corr.get(c["nombre"], c["nombre"])       # el dato del evento con otro nombre (D2)
                prop = nombres.pascal(dato)
                origen = next(((var, d[dato]) for var, d in fuentes_ev if dato in d), None)
                if origen is None:
                    args.append("null")
                elif origen[1]["opcional"] and not c["tipo"]["opcional"]:
                    args.append(f'({origen[0]}.{prop} ?? throw new DatoFaltante({cs_cadena(c["nombre"])}))')
                else:
                    args.append(f'{origen[0]}.{prop}')
            var_m = nombres.camel(cmd["nombre"])
            manejadores[var_m] = {"cs": cmd["manejador"], "var": var_m}
            x.update({"comando": cmd["nombre"], "comando_clase": cmd["clase"], "manejador_var": var_m,
                      "junto_con": junto, "grupo": [cs_cadena(g) for g in grupo] if junto else [],
                      "grupo_nombre": cs_cadena(cmd["nombre"]), "variables": variables, "args": args})
            self.registrar_externo(x)
        if self.externos:
            ctx = self.ctx
            self.render("receptor.g.cs.j2", f"{self.proyecto}/EventosExternos/ReceptorDeEventosExternos.g.cs",
                        externos=self.externos, manejadores=[manejadores[k] for k in sorted(manejadores)],
                        memoria=bool(requeridos), cabecera=self.cabecera("ApplicationComponent", ctx["nombre"], ctx["id"]))

    def registrar_externo(self, x: dict):
        """Guarda un evento de otro contexto ya preparado: su record, su trazabilidad y su endpoint."""
        nombre, clase = x["nombre"], x["clase"]
        self.externos.append(x)
        archivo = f"{self.proyecto}/EventosExternos/{clase}.g.cs"
        self.render("evento_externo.g.cs.j2", archivo, x=x, cabecera=self.cabecera("ApplicationEvent", nombre, x["id"]))
        receptor = f"{self.proyecto}/EventosExternos/ReceptorDeEventosExternos.g.cs"
        self.traza_de(x["id"], "ApplicationEvent", nombre, archivo, clase)
        self.traza_de(x["id"], "ApplicationEvent", nombre, receptor, "ReceptorDeEventosExternos")
        self.traza_de(x["id"], "ApplicationEvent", nombre, f"{self.proyecto}/Registro.g.cs", f'POST {x["ruta"]}')
