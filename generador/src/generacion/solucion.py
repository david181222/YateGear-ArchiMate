"""La solución completa: junta los contextos y escribe los archivos."""
from __future__ import annotations

from comun import nombres
from generacion.constantes import ARCHIVOS_GENERADOS, INTEGRACION, PRUEBAS_ENTRE_CONTEXTOS, PUERTO, TIPO_PROYECTO_CS
from generacion.csharp import ErrorDeGeneracion, valor_json
from validacion import valores

import json
import uuid
from pathlib import Path

from generacion.contexto import Generador

class Solucion:
    """Junta los contextos en una solución: host, bus entre contextos (Integracion), .sln y contextos.json."""

    def __init__(self, modelo: dict, specs_: list[dict], salida: Path, entre_contextos: list[dict] | None = None):
        self.m, self.salida = modelo, salida
        self.entre_contextos = entre_contextos or []
        self.modelo_nombre = modelo["generado_desde"]["modelo_nombre"]
        self.host = nombres.pascal(self.modelo_nombre)
        self.generadores = [Generador(modelo, s, salida) for s in specs_]
        proyectos = [g.proyecto for g in self.generadores]
        for nombre in sorted(set(proyectos)):
            if proyectos.count(nombre) > 1:
                raise ErrorDeGeneracion(f'dos YAML generan el mismo proyecto "{nombre}" (el mismo contexto)')
        for g in self.generadores:
            if g.proyecto in (self.host, INTEGRACION):
                raise ErrorDeGeneracion(f'el contexto "{g.ctx["nombre"]}" da el proyecto "{g.proyecto}", '
                                        f'que es el nombre del host o del bus entre contextos')
        self.env = self.generadores[0].env if self.generadores else None

    def render(self, plantilla: str, **datos) -> str:
        texto = self.env.get_template(plantilla).render(puerto=PUERTO, **datos)
        if "\r" in texto:
            raise ErrorDeGeneracion(f"{plantilla}: la salida tiene fin de línea CRLF")
        return texto

    def escenarios_entre_contextos(self, gs: list["Generador"]) -> list[dict]:
        """Los escenarios de punta a punta (S4), con la llamada HTTP de cada paso, su identidad y lo esperado.

        Cada paso va al contexto que dice en. Un dato de la entrada que se llama como una identidad ya creada en el
        escenario toma su valor (regla de los datos), así el arriendo y el yate pasan de un contexto a otro. Los
        consecutivos siguen de un escenario al siguiente, porque todos corren contra la misma aplicación.
        """
        por_contexto = {g.ctx["nombre"]: g for g in gs}
        envios = {m_["nombre"]: {"ruta_base": g.ruta_base, "nombre": m_["titulo"]}
                  for g in gs for e in g.emisores for m_ in e["mensajes"]}
        contador, salida = {}, []
        for spec in self.entre_contextos:
            for nombre_e, pasos in spec[valores.CLAVE_ENTRE_CONTEXTOS].items():
                actual, lista = {}, []
                for i, paso in enumerate(pasos, 1):
                    nombre, op = next(iter(paso.items()))
                    g = por_contexto[op["en"]]
                    esp = op.get("espera")
                    rechazo = isinstance(esp, int) or (isinstance(esp, dict) and "código" in esp)
                    p = g.paso_entre_contextos(nombre, op.get("con") or {}, actual, contador, rechazo)
                    if p["identidad"] and not rechazo:
                        actual[p["id_nombre"]] = p["identidad"]
                    if esp is None:
                        espera = {"tipo": "exito", "texto": "HTTP 2xx"}
                    elif isinstance(esp, int):
                        espera = {"tipo": "codigo", "valor": esp, "texto": f"HTTP {esp}"}
                    elif isinstance(esp, dict) and "código" in esp:
                        campos_e = {valores.CAMPOS_DE_ERROR[k]: (nombres.pascal(v) if k == "estado actual" else v)
                                    for k, v in esp.items() if k != "código"}
                        espera = {"tipo": "codigo", "valor": esp["código"], "campos": campos_e,
                                  "texto": f'HTTP {esp["código"]} y ' + ", ".join(f"{k} = {v}" for k, v in esp.items() if k != "código")}
                    elif isinstance(esp, (str, list)):
                        nombres_e = [esp] if isinstance(esp, str) else list(esp)
                        espera = {"tipo": "eventos", "eventos": [x for x in nombres_e if x not in envios],
                                  "envios": [envios[x] for x in nombres_e if x in envios],
                                  "texto": "HTTP 2xx y " + ", ".join(f'"{x}"' for x in nombres_e)}
                    else:
                        q = next(q_ for q_ in g.consultas if q_["nombre"] == nombre)
                        tipos_salida = {s_["nombre"]: s_["tipo"] for s_ in q["salida_campos"]}
                        espera = {"tipo": "salida", "valores": {nombres.camel(k): valor_json(v, tipos_salida[k]) for k, v in esp.items()},
                                  "texto": "HTTP 2xx y " + ", ".join(f"{k} = {v}" for k, v in esp.items())}
                    lista.append({"numero": i, "nombre": nombre, "contexto": op["en"], "tipo": p["tipo"], "crea": p["crea"],
                                  "identidad": p["identidad"], "metodo": p["metodo"], "ruta": p["ruta"],
                                  "cuerpo": p["cuerpo"], "espera": espera})
                salida.append({"nombre": nombre_e, "identidad": "", "pasos": lista})
        return salida

    def generar(self) -> dict:
        for g in self.generadores:
            g.generar()
        gs = sorted(self.generadores, key=lambda g: g.proyecto)
        archivos, manuales = {}, {}
        for g in gs:
            archivos.update(g.archivos)
            manuales.update(g.manuales)

        mid = self.m["generado_desde"]["modelo_id"]
        cab = Generador.cabecera("Model", self.modelo_nombre, mid)
        ns_integracion = f"{self.host}.{INTEGRACION}"
        contextos = [{"nombre": g.ctx["nombre"], "id": g.ctx["id"], "proyecto": g.proyecto, "ns": g.ns,
                      "ruta_base": g.ruta_base, "ancla": g.ruta_base.lstrip("/"), "rutas": g.rutas()} for g in gs]
        h, i = self.host, INTEGRACION
        archivos[f"{h}/{h}.csproj"] = self.render("host.csproj.j2", cabecera=cab, contextos=contextos, integracion=i)
        archivos[f"{h}/Program.g.cs"] = self.render("host_program.g.cs.j2", cabecera=cab, contextos=contextos,
                                                     ns_integracion=ns_integracion)
        archivos[f"{h}/Properties/launchSettings.json"] = self.render("launchSettings.json.j2", proyecto=h)
        # Página de inicio de la API (infraestructura): las rutas de cada contexto, servida como archivo estático.
        archivos[f"{h}/wwwroot/index.html"] = self.render("index.html.j2", cabecera=cab, contextos=contextos,
                                                          modelo=self.modelo_nombre)
        archivos[f"{i}/{i}.csproj"] = self.render("integracion.csproj.j2", cabecera=cab, ns_integracion=ns_integracion)
        archivos[f"{i}/BusEntreContextos.g.cs"] = self.render("integracion.g.cs.j2", cabecera=cab,
                                                               ns_integracion=ns_integracion)
        archivos["global.json"] = self.render("global.json.j2")

        def guid(semilla: str) -> str:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, f"archimate:{semilla}")).upper()

        proyectos = sorted([{"nombre": g.proyecto, "guid": guid(g.ctx["id"])} for g in gs]
                           + [{"nombre": h, "guid": guid(mid)}, {"nombre": i, "guid": guid(f"{mid}:{i}")}],
                           key=lambda x: x["nombre"])
        sln = f"{h}.sln"
        archivos[sln] = self.render("solucion.sln.j2", cabecera=cab, proyectos=proyectos, tipo_proyecto=TIPO_PROYECTO_CS)
        manifiesto = {"generado_desde": cab, "host": h, "puerto": PUERTO,
                      "contextos": [{"nombre": g.ctx["nombre"], "proyecto": g.proyecto, "ruta_base": g.ruta_base,
                                     "escenarios": g.escenarios_json, "trazabilidad": f"trazabilidad/{g.proyecto}.csv"}
                                    for g in gs]}
        if self.entre_contextos:                            # S4: escenarios de punta a punta entre contextos
            escenarios = self.escenarios_entre_contextos(gs)
            archivos[f"{PRUEBAS_ENTRE_CONTEXTOS}/escenarios.json"] = json.dumps(
                {"generado_desde": cab, "ruta_base": "", "entre_contextos": True,
                 "contextos": [g.ruta_base for g in gs], "escenarios": escenarios}, ensure_ascii=False, indent=2) + "\n"
            pruebas = gs[0].pruebas_de_escenarios(escenarios)
            for p in pruebas:
                if p["encabezado"]:
                    p["encabezado"] = p["encabezado"].removesuffix(" ()")
            archivos[f"{PRUEBAS_ENTRE_CONTEXTOS}/pruebas.http"] = self.render(
                "pruebas.http.j2", cabecera=cab, ruta_base="", pruebas=pruebas, con_escenarios=True, primero="")
            manifiesto["entre_contextos"] = f"{PRUEBAS_ENTRE_CONTEXTOS}/escenarios.json"
        archivos["contextos.json"] = json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n"
        for g in gs:
            for archivo in (f"{h}/Program.g.cs", f"{h}/{h}.csproj", f"{h}/wwwroot/index.html", sln, "global.json",
                            "contextos.json"):
                g.traza_de(g.ctx["id"], "ApplicationComponent", g.ctx["nombre"], archivo, "")
            archivos[f"trazabilidad/{g.proyecto}.csv"] = g.trazabilidad_csv()

        # Escribir. Lo generado se reescribe siempre; un manual solo si no existe.
        escritos, creados, conservados, borrados = 0, [], [], []
        for rel, texto in sorted(archivos.items()):
            destino = self.salida / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(texto.encode("utf-8"))
            escritos += 1
        for rel, texto in sorted(manuales.items()):
            destino = self.salida / rel
            if destino.exists():
                conservados.append(rel)
            else:
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(texto.encode("utf-8"))
                creados.append(rel)

        # Borrar lo generado que ya no corresponde: lo de la generación anterior que ya no se genera,
        # y los .g.cs sueltos en las carpetas de los proyectos. Los manuales nunca se borran.
        lista = self.salida / ARCHIVOS_GENERADOS
        anteriores = lista.read_text(encoding="utf-8").splitlines() if lista.is_file() else []
        sobran = {a for a in anteriores if a and a not in archivos and a not in manuales}
        for g in gs:
            for f in (self.salida / g.proyecto).rglob("*.g.cs"):
                rel = f.relative_to(self.salida).as_posix()
                if rel.split("/")[1] not in ("bin", "obj") and rel not in archivos:
                    sobran.add(rel)
        for rel in sorted(sobran):
            f = self.salida / rel
            if f.is_file():
                f.unlink()
                borrados.append(rel)
        lista.parent.mkdir(parents=True, exist_ok=True)
        lista.write_bytes(("\n".join(sorted(archivos)) + "\n").encode("utf-8"))

        # Carpetas con código a mano de un contexto que ya no se genera (se quitó su YAML): no se borran.
        proyectos = {g.proyecto for g in gs} | {h, i}
        sueltas = sorted(d.name for d in self.salida.iterdir()
                         if d.is_dir() and d.name not in proyectos and any(d.rglob("*.cs")))

        return {"escritos": escritos, "creados": creados, "conservados": conservados, "borrados": borrados,
                "huerfanos": [x for g in gs for x in g.huerfanos], "sueltas": sueltas,
                "avisos_escenarios": [(g.ctx["nombre"], a) for g in gs for a in getattr(g, "avisos_escenarios", [])],
                "contextos": [(g.ctx["nombre"], g.proyecto, len(set(g.traza))) for g in gs]}
