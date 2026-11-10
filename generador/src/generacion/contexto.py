"""Generador de un contexto: prepara en memoria todos sus archivos."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import jinja2

from comun import nombres, tipos
from generacion.comandos import Comandos
from generacion.constantes import (
    CARPETAS_MANUALES,
    DIR_PLANTILLAS,
    INFRAESTRUCTURA,
    INTEGRACION,
    MIEMBROS_RESERVADOS,
    PUERTO,
)
from generacion.consultas import Consultas
from generacion.csharp import cs_cadena, cs_tipo, ErrorDeGeneracion, xml
from generacion.escenarios import Escenarios
from generacion.eventos import Eventos
from generacion.politicas import Politicas
from generacion.raices import Raices
from generacion.servicios_sa import ServiciosSA


class Generador(Raices, ServiciosSA, Eventos, Comandos, Consultas, Politicas, Escenarios):
    """Genera un contexto. Cada parte (raíces, comandos, consultas...) está en su módulo."""

    def __init__(self, modelo: dict, spec: dict, salida: Path):
        self.m, self.s, self.salida = modelo, spec, salida
        self.ctx = next(c for c in modelo["contextos"] if c["nombre"] == spec["contexto"])
        dominio = self.ctx["nombre"].removeprefix("Contexto ")
        self.proyecto = nombres.pascal(dominio)
        self.ns_modelo = nombres.pascal(modelo["generado_desde"]["modelo_nombre"])
        self.ns = f'{self.ns_modelo}.{self.proyecto}'
        self.ns_integracion = f'{self.ns_modelo}.{INTEGRACION}'
        self.pruebas = f"pruebas/{self.proyecto}"           # pruebas.http y escenarios.json del contexto
        self.ruta_base = "/" + nombres.ruta(dominio)
        self.archivos: dict[str, str] = {}
        self.manuales: dict[str, str] = {}
        self.traza: list[tuple] = []
        self.tipos_cs: dict[str, str] = {n: "infraestructura" for n in INFRAESTRUCTURA}
        self.enums: dict[str, dict] = {}
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(DIR_PLANTILLAS), undefined=jinja2.StrictUndefined,
            trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True, autoescape=False)
        self.env.filters["xml"] = xml
        self.env.filters["cadena"] = cs_cadena

    # ------------------------------------------------------------ utilidades
    @staticmethod
    def cabecera(tipo: str, nombre: str, id_: str, codigo: str | None = None) -> str:
        return f'Generado desde ArchiMate: {tipo} "{nombre}" ({f"{codigo}, " if codigo else ""}{id_}).'

    def tipo_cs_nuevo(self, nombre: str, origen: str) -> str:
        if nombre in self.tipos_cs:
            raise ErrorDeGeneracion(f'dos elementos dan el mismo nombre de C# "{nombre}": {self.tipos_cs[nombre]} y {origen}')
        self.tipos_cs[nombre] = origen
        return nombre

    @staticmethod
    def revisar_miembros(clase: str, miembros: list[str]):
        vistos = set()
        for m in miembros:
            if m == clase or m in vistos or m in MIEMBROS_RESERVADOS:
                raise ErrorDeGeneracion(f'el nombre de C# "{m}" no se puede usar en {clase}: se repite, se llama como su clase '
                                        'o lo usa el generador. Cambia en el modelo o en el YAML el nombre del que sale')
            vistos.add(m)

    def tipo(self, texto: str, origen: str) -> dict:
        t = tipos.interpretar(texto)
        if t["enum"]:
            clase = nombres.pascal(t["enum"]["nombre"])
            e = self.enums.get(clase)
            if e is None:
                miembros = [nombres.pascal(v) for v in t["enum"]["valores"]]
                self.revisar_miembros(clase, miembros)
                e = self.enums[clase] = {"clase": self.tipo_cs_nuevo(clase, f'enum "{t["enum"]["nombre"]}"'),
                                         "nombre": t["enum"]["nombre"], "origenes": [],
                                         "miembros": [{"valor": v, "miembro": m} for v, m in zip(t["enum"]["valores"], miembros)]}
            elif e["nombre"] != t["enum"]["nombre"]:
                raise ErrorDeGeneracion(f'los enum "{e["nombre"]}" y "{t["enum"]["nombre"]}" dan el mismo nombre de C#')
            if origen not in e["origenes"]:
                e["origenes"].append(origen)
        return t

    def campos(self, mapa: dict | None, origen: str) -> list[dict]:
        out = []
        for k, v in (mapa or {}).items():
            t = self.tipo(v, origen)
            out.append({"nombre": k, "prop": nombres.pascal(k), "tipo": t, "cs": cs_tipo(t)})
        return out

    def traza_de(self, id_, tipo, nombre, archivo, clase):
        self.traza.append((id_, tipo, nombre, archivo, clase))

    def render(self, plantilla: str, destino: str, manual: bool = False, **datos):
        texto = self.env.get_template(plantilla).render(ns=self.ns, ns_integracion=self.ns_integracion,
                                                        puerto=PUERTO, **datos)
        if "\r" in texto:
            raise ErrorDeGeneracion(f"{plantilla}: la salida tiene fin de línea CRLF")
        (self.manuales if manual else self.archivos)[destino] = texto

    # ------------------------------------------------------------ todo el contexto
    def usar_objetos(self):
        """Fija los objetos de valor y las entidades de este contexto como los que se pueden usar en List<objeto de
        valor>. Se llama antes de interpretar tipos o valores del contexto: cada contexto tiene los suyos."""
        tipos.usar_objetos({v["nombre"]: {c["nombre"]: c for c in v["campos"]}
                            for a in self.ctx["agregados"] for v in a["objetos_valor"] + a["entidades"]})

    def generar(self) -> "Generador":
        """Prepara en memoria los archivos del contexto. Los escribe Solucion."""
        self.usar_objetos()
        self.preparar_raiz()
        self.preparar_sas()
        self.preparar_eventos()
        self.preparar_envios()
        self.preparar_comandos()
        self.preparar_consultas()
        self.preparar_politicas()
        self.preparar_eventos_externos()
        self.preparar_mensajes_sa()
        ctx = self.ctx
        cab_ctx = self.cabecera("ApplicationComponent", ctx["nombre"], ctx["id"])
        p = self.proyecto

        enums = sorted(self.enums.values(), key=lambda e: e["clase"])
        self.render("enums.g.cs.j2", f"{p}/Dominio/Enums.g.cs", enums=enums, cabecera=cab_ctx)
        self.render("infraestructura.g.cs.j2", f"{p}/Infraestructura/Infraestructura.g.cs", cabecera=cab_ctx)
        envios = [{**m_, "sa": e["sa"]["nombre"], "interfaz": e["interfaz"]} for e in self.emisores for m_ in e["mensajes"]]
        self.render("politicas.g.cs.j2", f"{p}/Politicas/Politicas.g.cs", politicas=self.politicas, grupos=self.grupos,
                    envios=envios, cabecera=cab_ctx)
        self.render("registro.g.cs.j2", f"{p}/Registro.g.cs", cabecera=cab_ctx, contexto=ctx["nombre"],
                    raices=[x["raiz"] for x in self.raices.values()], emisores=self.emisores, grupos=self.grupos,
                    sas=list(self.sas.values()), comandos=self.comandos, consultas=self.consultas,
                    externos=self.externos, ruta_base=self.ruta_base, receptores_sa=self.receptores_sa,
                    temporizadores=[c["temporizador"] for c in self.comandos if c["temporizador"]],
                    memoria=any(c["requeridos"] for c in self.comandos))
        self.escenarios_json = None
        if self.s.get("escenarios"):
            escenarios = self.preparar_escenarios()
            pruebas = self.pruebas_de_escenarios(escenarios)
            self.escenarios_json = f"{self.pruebas}/escenarios.json"
            self.archivos[self.escenarios_json] = json.dumps(
                {"generado_desde": cab_ctx, "ruta_base": self.ruta_base, "escenarios": escenarios},
                ensure_ascii=False, indent=2) + "\n"
            self.traza_de(ctx["id"], "ApplicationComponent", ctx["nombre"], self.escenarios_json, "")
        else:
            escenarios, pruebas = [], self.preparar_pruebas()
        consecutivas = [x["raiz"] for x in self.raices.values() if x["raiz"]["consecutivo"]]
        self.render("pruebas.http.j2", f"{self.pruebas}/pruebas.http", cabecera=cab_ctx, ruta_base=self.ruta_base,
                    pruebas=pruebas, con_escenarios=bool(escenarios),
                    primero=consecutivas[0]["prefijo"] + "1".zfill(consecutivas[0]["digitos"]) if consecutivas else "")
        for archivo, clase in [(f"{p}/{p}.csproj", ""), (f"{p}/Registro.g.cs", "Registro"),
                               (f"{p}/Infraestructura/Infraestructura.g.cs", "infraestructura"),
                               (f"{p}/Dominio/Enums.g.cs", "enums"), (f"{self.pruebas}/pruebas.http", "")]:
            self.traza_de(ctx["id"], "ApplicationComponent", ctx["nombre"], archivo, clase)

        # Manuales huérfanos: un .cs manual sin su .g.cs. No se borran; se sacan de la compilación.
        self.huerfanos = []
        for carpeta in CARPETAS_MANUALES:
            d = self.salida / p / carpeta
            if d.is_dir():
                for f in sorted(d.glob("*.cs")):
                    if f.name.endswith(".g.cs"):
                        continue
                    rel = f"{p}/{carpeta}/{f.name}"
                    if f"{p}/{carpeta}/{f.stem}.g.cs" not in self.archivos:
                        self.huerfanos.append(rel)
        self.render("proyecto.csproj.j2", f"{p}/{p}.csproj", cabecera=cab_ctx, integracion=INTEGRACION,
                    huerfanos=[{"ruta": h.removeprefix(f"{p}/").replace("/", "\\"),
                                "falta": h.removeprefix(f"{p}/").removesuffix(".cs").replace("/", "\\") + ".g.cs"}
                               for h in self.huerfanos])
        return self

    def rutas(self) -> list[dict]:
        """Las rutas del contexto para la página de inicio de la API (index.html): método, ruta, qué es y si se puede
        abrir directo en el navegador (un GET sin datos en la ruta ni en la consulta)."""
        out = []
        for q in sorted(self.consultas, key=lambda x: x["codigo"]):
            params = "&".join(f'{nombres.camel(c["nombre"])}=...' for c in q["entrada_campos"])
            ruta = q["ruta"] + (f"?{params}" if params else "")
            out.append({"metodo": "GET", "ruta": ruta, "enlace": "{" not in ruta and "?" not in ruta,
                        "que": f'Consulta {q["codigo"]} "{q["nombre"]}"'})
        for c in sorted(self.comandos, key=lambda x: x["codigo"]):
            out.append({"metodo": "POST", "ruta": c["ruta"], "enlace": False, "que": f'Comando {c["codigo"]} "{c["nombre"]}"'})
        for x in self.externos:
            out.append({"metodo": "POST", "ruta": x["ruta"], "enlace": False,
                        "que": f'Evento "{x["nombre"]}" de {x["de"]} (para pruebas: por el bus llega solo)'})
        for m in sorted(self.mensajes, key=lambda x: x["ruta"]):
            out.append({"metodo": "POST", "ruta": m["ruta"], "enlace": False, "que": f'Mensaje que recibe {m["titulo"]}'})
        out.append({"metodo": "GET", "ruta": f"{self.ruta_base}/bitacora", "enlace": True,
                    "que": "Bitácora (infraestructura): eventos, llamadas a los SA simulados y errores, en orden"})
        return out

    def trazabilidad_csv(self) -> str:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["ID ArchiMate", "tipo", "nombre", "archivo generado", "clase"])
        for fila in sorted(set(self.traza)):
            w.writerow(fila)
        return buf.getvalue()
