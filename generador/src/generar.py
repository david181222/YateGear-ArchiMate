"""Genera la solución C# desde modelo-ddd.json y los YAML de especificaciones, uno por contexto.

Cada contexto con YAML es un proyecto (biblioteca) con su registro: servicios, políticas y
endpoints. Un proyecto host, con el nombre del modelo, los levanta todos en un solo programa,
y el proyecto Integracion tiene el bus entre contextos (D1): los eventos viajan por nombre y
en JSON, y ningún contexto referencia a otro. Los contextos sin YAML no se generan.

Primero revisa cada YAML con specs.py; si hay errores, no genera nada.
Escribe:
  - los archivos generados (.g.cs, los de proyecto, pruebas y contextos.json), siempre;
  - los archivos manuales (.cs), solo si no existen;
  - trazabilidad/<Proyecto>.csv, uno por contexto.
Borra los archivos generados que ya no corresponden y avisa de los manuales huérfanos.

uso: python src/generar.py <modelo-ddd.json> <carpeta de salida> <specs.yaml> [<specs.yaml> ...]
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import sys
import textwrap
import uuid
from pathlib import Path

import jinja2

import nombres
import specs
import tipos

DIR_PLANTILLAS = Path(__file__).resolve().parent.parent / "plantillas"
TIPO_PROYECTO_CS = "9A19103F-16F7-4668-BE54-9A1E7A4F7556"     # tipo de proyecto "C# SDK" en una solución
CARPETAS_MANUALES = ("Comandos", "Consultas")
PUERTO = 5080                       # puerto de la aplicación: launchSettings.json y pruebas.http
INTEGRACION = "Integracion"         # proyecto con el bus entre contextos (D1)
ARCHIVOS_GENERADOS = "intermedio/archivos-generados.txt"   # para borrar los que ya no corresponden
INFRAESTRUCTURA = ("IRaiz", "IEvento", "Repositorio", "Bitacora", "RegistroDeBitacora", "BusDeEventos",
                   "RespuestaDeComando", "ReglaIncumplida", "NoEncontrado", "DatoFaltante", "Politicas", "Program",
                   "TransicionInvalida", "Estados", "EsperaDeEventos", "RespuestaDeEventoExterno",
                   "ReceptorDeEventosExternos", "Registro", "LectorDeEventos", "IdentidadRepetida",
                   "FaltaEventoRequerido", "MemoriaDeEventos",
                   "Json", "BusEntreContextos", "EventoEntreContextos")     # del bus entre contextos, que todo contexto importa
MIEMBROS_RESERVADOS = {"Manejar", "ValidarReglas", "Publicar", "Llamar"}


class ErrorDeGeneracion(Exception):
    pass


# ------------------------------------------------------------ tipos y literales de C#

def cs_tipo(t: dict) -> str:
    base = nombres.pascal(t["enum"]["nombre"]) if t["base"] == "enum" else \
        nombres.pascal(t["objeto"]) if t["base"] == "objeto" else t["base"]
    texto = f"List<{base}>" if t["lista"] else base
    return texto + ("?" if t["opcional"] else "")


def cs_cadena(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def cs_literal(v, t: dict) -> str:
    if v is None:
        return "null"
    if t["lista"]:
        uno = {**t, "lista": False, "opcional": False}
        return "[" + ", ".join(cs_literal(x, uno) for x in v) + "]"
    b = t["base"]
    if b == "enum":
        return f'{nombres.pascal(t["enum"]["nombre"])}.{nombres.pascal(v)}'
    if b == "string":
        return cs_cadena(v)
    if b == "int":
        return str(v)
    if b == "decimal":
        return f"{v}m"
    if b == "bool":
        return "true" if v else "false"
    if b == "DateOnly":
        d = datetime.date.fromisoformat(v)
        return f"new DateOnly({d.year}, {d.month}, {d.day})"
    d = datetime.datetime.fromisoformat(v)
    return f"new DateTime({d.year}, {d.month}, {d.day}, {d.hour}, {d.minute}, {d.second})"


def provisional(t: dict) -> str:
    """Valor provisional de un dato calculado, sin advertencias del compilador."""
    if t["opcional"]:
        return "null"
    if t["lista"]:
        return "[]"
    return {"string": '""', "int": "0", "decimal": "0m", "bool": "false"}.get(t["base"], "default")


def ejemplo(nombre: str, t: dict):
    """Valor de ejemplo, fijo, para pruebas.http."""
    if t["lista"]:
        return [ejemplo(nombre, {**t, "lista": False})]
    b = t["base"]
    if b == "enum":
        return nombres.pascal(t["enum"]["valores"][0])
    if b == "objeto":                       # un elemento de List<objeto de valor>: sus campos con valores de ejemplo
        return {nombres.camel(k): ejemplo(k, c) for k, c in tipos.OBJETOS[t["objeto"]].items()}
    return {"string": nombre, "int": 1, "decimal": 100, "bool": True,
            "DateOnly": "2026-02-01", "DateTime": "2026-02-01T09:00:00"}[b]


def valor_json(v, t: dict):
    """Un valor del YAML tal como viaja en JSON (los enum, con su nombre de C#; los objetos de valor, en camelCase)."""
    if v is None:
        return v
    if t["base"] == "objeto":
        campos = tipos.OBJETOS[t["objeto"]]
        return [{nombres.camel(k): valor_json(x, campos[k]) for k, x in e.items()} for e in v]
    if t["base"] == "enum":
        return [nombres.pascal(x) for x in v] if t["lista"] else nombres.pascal(v)
    return v


def xml(texto: str) -> str:
    return " ".join(texto.split("\n")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lineas(texto: str, ancho: int = 100) -> list[str]:
    out = []
    for parrafo in texto.split("\n"):
        out += textwrap.wrap(parrafo, ancho) or [""]
    return out


class Ambito:
    """Datos disponibles por nombre (regla de los datos). La última capa agregada gana."""

    def __init__(self):
        self.capas: list[dict] = []

    def agregar(self, capa: dict):
        self.capas.append(capa)

    def con(self, capa: dict) -> "Ambito":
        """Una copia con una capa más, que gana sobre las anteriores."""
        a = Ambito()
        a.capas = self.capas + [capa]
        return a

    def buscar(self, nombre: str):
        for capa in reversed(self.capas):
            if nombre in capa:
                return capa[nombre]
        return None

    def expr(self, nombre: str, destino_opcional: bool) -> str:
        f = self.buscar(nombre)
        if f is None:
            raise ErrorDeGeneracion(f'el dato "{nombre}" no está disponible')
        e = f["opcional"] if destino_opcional else f["requerido"]
        if f["tipo"]["opcional"] and not destino_opcional:
            e = f'({e} ?? throw new DatoFaltante({cs_cadena(nombre)}))'
        return e


def fuente(expr: str, t: dict, expr_opcional: str | None = None) -> dict:
    return {"requerido": expr, "opcional": expr_opcional or expr, "tipo": t}


# ------------------------------------------------------------ generador

class Generador:
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
                raise ErrorDeGeneracion(f'el miembro "{m}" de {clase} se repite, se llama como su clase o es reservado')
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

    # ------------------------------------------------------------ raíz y objetos de valor
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
        if ag["entidades"]:
            raise ErrorDeGeneracion(f'"{ag["nombre"]}" tiene entidades; el generador todavía no las genera (G9)')
        r = ag["raiz"]
        sr = self.s["raices"][r["nombre"]]
        ident = sr["identidad"]
        clase = self.tipo_cs_nuevo(nombres.pascal(r["nombre"]), f'raíz "{r["nombre"]}"')
        estado_t = self.tipo(sr["estado"], f'estado de la raíz "{r["nombre"]}" (YAML)')
        var = nombres.camel(r["nombre"])
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
        for v in ag["objetos_valor"]:
            vclase = self.tipo_cs_nuevo(nombres.pascal(v["nombre"]), f'objeto de valor "{v["nombre"]}"')
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
                  "comp_id": v["composicion_id"], "campos": campos, "decl": decl}
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
            self.render("objeto_valor.g.cs.j2", f"{dom}/{vo['clase']}.g.cs", v=vo, raiz=raiz,
                        cabecera=self.cabecera("DataObject", vo["nombre"], vo["id"]))
            self.traza_de(vo["id"], "DataObject", vo["nombre"], f"{dom}/{vo['clase']}.g.cs", vo["clase"])
            self.traza_de(vo["comp_id"], "Composition", f'{r["nombre"]} -> {vo["nombre"]}',
                          f"{dom}/{clase}.g.cs", f'{clase}.{vo["prop"]}')
        for obj in [r] + ag["objetos_valor"]:
            for c in obj["campos"]:
                if c["enum"]:
                    self.traza_de(obj["id"], "DataObject", f'{obj["nombre"]} (campo "{c["nombre"]}")',
                                  f"{dom}/Enums.g.cs", nombres.pascal(c["enum"]["nombre"]))

    def ambito_raiz(self) -> Ambito:
        a = Ambito()
        capa = {}
        for k, f in self.fuentes_raiz.items():
            capa[k] = f
        a.agregar(capa)
        return a

    # ------------------------------------------------------------ servicios SA
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
                  "var": nombres.camel(msa["nombre"]), "entrada_campos": ent, "salida_campos": sal,
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

    # ------------------------------------------------------------ eventos
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

    # ------------------------------------------------------------ comandos
    def preparar_comandos(self):
        self.comandos = []
        ev_por_id = {e["id"]: e["nombre"] for e in self.ctx["eventos"]}
        for mc in self.ctx["comandos"]:
            r = self.usar_raiz(mc["raiz_id"])          # la raíz del agregado del comando (G2)
            v = r["var"]
            sc = self.s["comandos"][mc["nombre"]]
            clase = nombres.pascal(mc["nombre"])
            n = {k: self.tipo_cs_nuevo(x, f'comando "{mc["nombre"]}"') for k, x in
                 {"clase": clase, "datos": f"{clase}Datos", "manejador": f"{clase}Manejador"}.items()}
            crea = sc.get("crea") is True
            si_no_existe = sc.get("crea") == "si_no_existe"   # carga la raíz y, si no existe, la crea vacía
            todas = sc.get("sobre") == "todas"            # G8: elige raíces y publica un evento por cada una

            def estado(nombre_estado):                # literal de C# de un estado de la raíz
                return f'{r["estado_clase"]}.{nombres.pascal(nombre_estado)}'

            ent = self.campos(sc.get("entrada"), f'entrada de "{mc["nombre"]}" (YAML)')
            params = ([] if crea or todas else [{"cs": "string", "prop": r["id_prop"]}]) + ent
            self.revisar_miembros(clase, [p["prop"] for p in params])
            capa_ent = {c["nombre"]: fuente(f'comando.{c["prop"]}', c["tipo"]) for c in ent}

            antes = Ambito()                       # antes de guardar
            if not crea and not todas:
                antes.agregar(dict(self.fuentes_raiz))
            antes.agregar(capa_ent)
            # Valores fijos del comando (YAML: valores).
            capa_val = {k: fuente(cs_literal(x, self.tipos_raiz[k]), self.tipos_raiz[k])
                        for k, x in (sc.get("valores") or {}).items()}
            antes.agregar(capa_val)
            llamadas, deps, datos_props, datos_args = [], [], [], ["comando"]
            datos_props.append({"cs": clase, "prop": "Comando"})
            otras = [self.raices[self.usar_raiz(x["raiz_id"])["nombre"]]["raiz"] for x in mc["lee_tambien"]]
            self.usar_raiz(mc["raiz_id"])
            if todas:                                  # todas las raíces, y las demás que lee (G8)
                datos_props.append({"cs": f'IReadOnlyList<{r["clase"]}>', "prop": "Raices"})
                datos_args.append("raices")
                for o in otras:
                    datos_props.append({"cs": f'IReadOnlyList<{o["clase"]}>', "prop": o["clase"]})
                    datos_args.append(f'{o["repositorio"]}.Todas()')
            elif not crea:
                datos_props.append({"cs": r["clase"], "prop": r["clase"]})
                datos_args.append(v)
            # Eventos de otros contextos que el comando requiere (D5): se buscan en la memoria por su identidad.
            requeridos, capas_req = [], []
            for nombre_ev in sc.get("requiere") or []:
                x = self.s["eventos_de_otros_contextos"][nombre_ev]
                ev_clase, var_ev = nombres.pascal(nombre_ev), nombres.camel(nombre_ev)
                id_ev = x.get("identidad") or r["id_nombre"]
                requeridos.append({"var": var_ev, "clase": ev_clase, "nombre": cs_cadena(nombre_ev),
                                   "identidad": antes.expr(id_ev, False)})
                capa = {k: fuente(f"{var_ev}.{nombres.pascal(k)}", tipos.interpretar(tx))
                        for k, tx in (x.get("datos") or {}).items()}
                antes.agregar(capa)
                capas_req.append(capa)
                datos_props.append({"cs": ev_clase, "prop": ev_clase})
                datos_args.append(var_ev)
            if requeridos:
                deps.append({"cs": "MemoriaDeEventos", "var": "memoria"})
            # Otras raíces que el comando lee (G6): se cargan por el dato con el nombre de su identidad; 404 si no existen.
            leidas = []
            for o in otras:
                deps.append({"cs": f'Repositorio<{o["clase"]}>', "var": o["repositorio"]})
                if todas:
                    continue
                leidas.append({"var": o["var"], "repositorio": o["repositorio"], "clase": o["clase"],
                               "identidad": antes.expr(o["id_nombre"], False), "nombre": o["nombre"].lower()})
                datos_props.append({"cs": o["clase"], "prop": o["clase"]})
                datos_args.append(o["var"])
            capas_sa = []
            for nombre_sa in sc.get("usa") or []:
                sa = self.sas[nombre_sa]
                args = [antes.expr(c["nombre"], c["tipo"]["opcional"]) for c in sa["entrada_campos"]]
                var_resp = "respuesta" + sa["clase"]
                llamadas.append({"var": var_resp, "servicio": sa["var"], "entrada": sa["entrada"], "args": args})
                if sa["var"] not in [d["var"] for d in deps]:
                    deps.append({"cs": sa["interfaz"], "var": sa["var"]})
                capa = {c["nombre"]: fuente(f'{var_resp}.{c["prop"]}', c["tipo"]) for c in sa["salida_campos"]}
                antes.agregar(capa)
                capas_sa.append(capa)
                datos_props.append({"cs": sa["salida"], "prop": sa["clase"]})
                datos_args.append(var_resp)

            resultados, enum_res = [], None
            eventos_cmd = []
            if sc.get("resultados"):
                enum_res = self.tipo_cs_nuevo(f"{clase}Resultado", f'resultados de "{mc["nombre"]}"')
                for ev, rr in sc["resultados"].items():
                    partes = []
                    for campo, vals in rr["si"].items():
                        f = antes.buscar(campo)
                        t = {**f["tipo"], "opcional": False}
                        e = antes.expr(campo, True)
                        partes.append("(" + " || ".join(f"{e} == {cs_literal(x, t)}" for x in vals) + ")")
                    resultados.append({"miembro": nombres.pascal(ev), "evento": ev, "condicion": " && ".join(partes),
                                       "desde": [estado(x) for x in rr.get("desde") or []],
                                       "a": estado(rr["a"]) if rr.get("a") else None,
                                       "operacion": cs_cadena(f'{mc["nombre"]}: {ev}')})
                    eventos_cmd.append(ev)
                self.revisar_miembros(enum_res, [x["miembro"] for x in resultados])
                datos_props.append({"cs": enum_res, "prop": "Resultado"})
                datos_args.append("resultado")
            else:
                eventos_cmd = list(sc.get("eventos") or [])
            self.revisar_miembros(n["datos"], [p["prop"] for p in datos_props])

            # Lo que guarda (después de ValidarReglas): el comando y, si tiene resultados, cada resultado.
            asignaciones, operaciones = self.guardar(sc.get("guarda"), antes, r)
            if crea:
                asignaciones.insert(0, {"prop": "Estado", "expr": f'{r["estado_clase"]}.{nombres.pascal(sc["a"])}'})
            capas_val_r = {}
            for x in resultados:
                rr = sc["resultados"][x["evento"]]
                capas_val_r[x["evento"]] = {k: fuente(cs_literal(val, self.tipos_raiz[k]), self.tipos_raiz[k])
                                            for k, val in (rr.get("valores") or {}).items()}
                x["asignaciones"], x["operaciones"] = self.guardar(rr.get("guarda"), antes.con(capas_val_r[x["evento"]]), r)

            # Identidad formada con datos (G3): sus partes que no son campos se guardan en la raíz, y la identidad
            # se arma uniéndolas con "/". Al agregarla, el repositorio responde 409 si ya existe.
            identidad_expr, partes_obligatorias = None, []
            if crea and not r["consecutivo"]:
                # Las partes de texto que llegan en la entrada no pueden faltar (si no, la identidad quedaría a medias).
                for parte in r["id_de"]:
                    f_parte = antes.buscar(parte)
                    if f_parte and f_parte["tipo"]["base"] == "string" and f_parte["requerido"].startswith("comando."):
                        partes_obligatorias.append({"expr": f_parte["requerido"], "nombre": cs_cadena(parte)})
                for comp in r["componentes"]:
                    asignaciones.append({"prop": comp["prop"], "expr": antes.expr(comp["nombre"], False)})
                partes = []
                for parte in r["id_de"]:
                    fuente_parte = antes.buscar(parte)
                    if fuente_parte is None:              # campo de la raíz que solo se guarda: se toma de la raíz nueva
                        fuente_parte = self.fuentes_raiz[parte]
                        e = fuente_parte["requerido"]
                    else:
                        e = antes.expr(parte, False)
                    # Las fechas, en formato fijo e independiente del idioma del equipo (2026-03-10T10:00:00).
                    formato = {"DateTime": '"s"', "DateOnly": '"yyyy-MM-dd"'}.get(fuente_parte["tipo"]["base"])
                    partes.append(f"({e}).ToString({formato}, System.Globalization.CultureInfo.InvariantCulture)" if formato else e)
                identidad_expr = '$"' + "/".join("{(" + x + ")}" for x in partes) + '"'

            # Eventos (después de guardar: ya hay raíz e identidad).
            despues = Ambito()
            despues.agregar(dict(self.fuentes_raiz))
            despues.agregar(capa_ent)
            despues.agregar(capa_val)
            for capa in capas_req + capas_sa:
                despues.agregar(capa)
            calculados, vistos = [], set()
            publicar = {}
            for nombre_ev in eventos_cmd:
                ev = self.eventos[nombre_ev]
                amb_ev = despues.con(capas_val_r.get(nombre_ev, {}))     # con los valores de su resultado
                args = [f'{v}.{r["id_prop"]}']
                args += [amb_ev.expr(d["nombre"], d["tipo"]["opcional"]) for d in ev["datos"]]
                for k in ev["calculados"]:
                    if k["prop"] not in vistos:
                        vistos.add(k["prop"])
                        calculados.append({"nombre": k["nombre"], "metodo": k["prop"], "cs": k["cs"],
                                           "tipo_yaml": k["tipo"]["tipo"], "evento": nombre_ev,
                                           "provisional": provisional(k["tipo"])})
                    args.append(f'{k["prop"]}(datos)')
                publicar[nombre_ev] = {"clase": ev["clase"], "args": args}
            for x in resultados:
                x["publicar"] = [publicar[x["evento"]]]
            self.revisar_miembros(n["manejador"], [k["metodo"] for k in calculados])
            eventos_modelo = sorted(ev_por_id[i] for i in mc["eventos"])
            if sorted(eventos_cmd) != eventos_modelo:
                raise ErrorDeGeneracion(f'"{mc["nombre"]}": los eventos del YAML no son los del modelo')

            k = mc["contrato"]
            com = {**n, "nombre": mc["nombre"], "codigo": mc["codigo"], "id": mc["id"], "crea": crea,
                   "parametros": params, "datos_props": datos_props, "datos_args": datos_args,
                   "dependencias": [{"cs": f'Repositorio<{r["clase"]}>', "var": "repositorio"},
                                    {"cs": "BusDeEventos", "var": "bus"}] + deps,
                   "llamadas": llamadas, "resultados": resultados, "enum_resultado": enum_res,
                   "requeridos": requeridos, "identidad_expr": identidad_expr, "operaciones": operaciones,
                   "leidas": leidas, "todas": todas, "temporizador": self.temporizador(sc, clase, n, ent) if todas else None,
                   "raiz_nombre": r["nombre"], "si_no_existe": si_no_existe,
                   "id_cadena": cs_cadena(r["id_nombre"]), "partes_obligatorias": partes_obligatorias, "estado_inicial": estado(self.raiz["estado_t"]["enum"]["valores"][0]),
                   "resultados_con_guarda": [x for x in resultados if x["asignaciones"] or x["operaciones"]],
                   "operacion": cs_cadena(mc["nombre"]),
                   "desde": [] if crea else [estado(x) for x in sc.get("desde") or []],
                   "a": estado(sc["a"]) if sc.get("a") and not crea else None,
                   "resultados_con_desde": [x for x in resultados if x["desde"]],
                   "resultados_con_a": [x for x in resultados if x["a"]],
                   "sin_resultado": cs_cadena(f'Ningún resultado de "{mc["nombre"]}" se cumple con estos datos.'),
                   "escribe": crea or si_no_existe or mc["acceso"] in ("escritura", "lectura y escritura"),
                   "asignaciones": asignaciones, "eventos": [publicar[e] for e in eventos_cmd],
                   "calculados": calculados, "contrato": k, "servicio_negocio": mc["servicio_negocio"],
                   "reglas": lineas(k["reglas"]) if k["reglas"] else ["El contrato no tiene reglas."],
                   "salida_contrato": lineas(k["salida"]),
                   "ruta": f'{self.ruta_base}/comandos/{nombres.ruta(mc["nombre"])}',
                   "archivo": f'{self.proyecto}/Comandos/{clase}.g.cs',
                   "manual": f'{self.proyecto}/Comandos/{clase}.cs', "spec": sc, "entrada_campos": ent}
            self.comandos.append(com)
            cab = self.cabecera("ApplicationProcess", mc["nombre"], mc["id"], mc["codigo"])
            self.render("comando.g.cs.j2", com["archivo"], c=com, raiz=r, cabecera=cab)
            self.render("comando_manual.cs.j2", com["manual"], manual=True, c=com, raiz=r, cabecera=cab)
            for x in ("clase", "datos", "manejador"):
                self.traza_de(mc["id"], "ApplicationProcess", mc["nombre"], com["archivo"], n[x])
            self.traza_de(mc["id"], "ApplicationProcess", mc["nombre"], com["manual"], f'{n["manejador"]} (manual)')
            self.traza_de(mc["id"], "ApplicationProcess", mc["nombre"], f"{self.proyecto}/Registro.g.cs", f'POST {com["ruta"]}')
            if mc["acceso_id"]:
                self.traza_de(mc["acceso_id"], "Access", f'{mc["nombre"]} -> {r["nombre"]} ({mc["acceso"]})', com["archivo"], n["manejador"])
            for lt in mc["lee_tambien"]:
                self.traza_de(lt["acceso_id"], "Access", f'{mc["nombre"]} -> otra raíz (lectura)', com["archivo"], n["manejador"])
            self.traza_de(mc["servicio_negocio"]["id"], "BusinessService", mc["servicio_negocio"]["nombre"], com["archivo"], n["manejador"])
            self.traza_de(k["id"], "Contract", k["nombre"], com["archivo"], n["manejador"])
            self.traza_de(k["id"], "Contract", k["nombre"], com["manual"], f'{n["manejador"]}.ValidarReglas (manual)')

    def temporizador(self, sc: dict, clase: str, n: dict, ent: list[dict]) -> dict | None:
        """El temporizador de un comando sobre todas (G8, YAML: temporizador): corre el comando cada N minutos con
        los valores de con y la hora actual en el dato de ahora."""
        x = sc.get("temporizador")
        if not x:
            return None
        nombre = self.tipo_cs_nuevo(f"{clase}Temporizador", f'temporizador de "{sc}"')
        con, ahora = x.get("con") or {}, x.get("ahora")
        args = [cs_literal(con[c["nombre"]], c["tipo"]) if c["nombre"] in con else "DateTime.Now" if c["nombre"] == ahora
                else "null" for c in ent]
        return {"clase": nombre, "minutos": x["cada minutos"], "args": args, "manejador": n["manejador"], "comando": clase}

    def guardar(self, guarda, amb: Ambito, r: dict) -> tuple[list[dict], list[str]]:
        """Lo que escribe en la raíz (YAML: guarda). Devuelve las asignaciones (propiedad = expresión) y las
        operaciones sobre listas (sentencias de C#) de los objetos de valor con Cardinalidad Muchos (G4)."""
        asignaciones, operaciones = [], []
        v = r["var"]

        def nuevo(vo):
            args = [amb.expr(c["nombre"], c["tipo"]["opcional"]) if amb.buscar(c["nombre"]) else "null" for c in vo["campos"]]
            return f'new {vo["clase"]}({", ".join(args)})'

        for g in guarda or []:
            if isinstance(g, dict) and next(iter(g)) in self.vos:      # operación sobre una lista
                nombre_vo, op = next(iter(g.items()))
                vo = self.vos[nombre_vo]
                lista = f'{v}.{vo["prop"]}'
                if op == "agregar":
                    operaciones.append(f"{lista}.Add({nuevo(vo)});")
                    continue
                tipo_op, claves = next(iter(op.items()))
                if tipo_op == "todos":                   # la lista entera, con un dato List<objeto de valor>
                    asignaciones.append({"prop": vo["prop"], "expr": f"[.. ({amb.expr(claves, True)} ?? [])]"})
                    continue
                props = {c["nombre"]: c["prop"] for c in vo["campos"]}
                pred = " && ".join(f'e.{props[k]} == {amb.expr(k, True)}' for k in claves)
                if tipo_op == "quitar":                  # no falla si ya no estaba
                    operaciones.append(f"{lista}.RemoveAll(e => {pred});")
                else:                                    # reemplazar: 404 si no hay ninguno con esa clave
                    falta = cs_cadena(f'No hay un "{nombre_vo}" con ese {" y ".join(claves)}.')
                    operaciones.append(f"if ({lista}.RemoveAll(e => {pred}) == 0) throw new NoEncontrado({falta});")
                    operaciones.append(f"{lista}.Add({nuevo(vo)});")
            elif isinstance(g, dict):                    # {campo de la raíz: dato}
                campo, dato = next(iter(g.items()))
                c = next(x for x in r["campos"] if x["nombre"] == campo)
                asignaciones.append({"prop": c["prop"], "expr": amb.expr(dato, tipos.interpretar(c["tipo_yaml"])["opcional"])})
            elif g in self.vos:
                vo = self.vos[g]
                asignaciones.append({"prop": vo["prop"], "expr": nuevo(vo)})
            else:
                c = next(x for x in r["campos"] if x["nombre"] == g)
                asignaciones.append({"prop": c["prop"], "expr": amb.expr(g, tipos.interpretar(c["tipo_yaml"])["opcional"])})
        return asignaciones, operaciones

    # ------------------------------------------------------------ consultas
    def preparar_consultas(self):
        self.consultas = []
        for mq in self.ctx["consultas"]:
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
                               "expr": f"elementos"})
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

    # ------------------------------------------------------------ políticas
    def preparar_politicas(self):
        ev_por_id = {e["id"]: e["nombre"] for e in self.ctx["eventos"]}
        cmd_por_id = {c["id"]: c for c in self.comandos}
        self.politicas = []
        for p in self.ctx["politicas"]:
            ev = self.eventos[ev_por_id[p["evento_id"]]]
            r = self.usar_raiz(ev["raiz"])
            cmd = cmd_por_id[p["comando_id"]]
            props_ev = {d["nombre"]: d for d in ev["datos"] + ev["calculados"]}
            args = [f'e.{r["id_prop"]}']
            for c in cmd["entrada_campos"]:
                d = props_ev.get(c["nombre"])
                if d is None:
                    args.append("null")
                elif d["tipo"]["opcional"] and not c["tipo"]["opcional"]:
                    args.append(f'(e.{d["prop"]} ?? throw new DatoFaltante({cs_cadena(c["nombre"])}))')
                else:
                    args.append(f'e.{d["prop"]}')
            self.politicas.append({"relacion_id": p["relacion_id"], "evento": ev["nombre"], "evento_clase": ev["clase"],
                                   "comando": cmd["nombre"], "comando_clase": cmd["clase"],
                                   "manejador": cmd["manejador"], "args": args})
            self.traza_de(p["relacion_id"], "Triggering", f'{ev["nombre"]} -> {cmd["nombre"]}',
                          f"{self.proyecto}/Politicas/Politicas.g.cs", "Politicas")

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
            # La raíz del evento: la del comando que dispara (G2). Sin dispara, la identidad se escribe en el YAML.
            r = self.usar_raiz(cmd_por_nombre[se["dispara"]]["raiz_nombre"]) if "dispara" in se else self.raiz
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
                 "id_nombre": id_nombre, "id_prop": id_prop, "parametros": params,
                 "recordar": nombre in requeridos, "comando": None, "grupo": [], "junto_con": [],
                 "ruta": f'{self.ruta_base}/eventos-externos/{nombres.ruta(nombre)}', "datos_campos": datos,
                 "obligatorios": ", ".join(f"({cs_cadena(p)}, {cs_cadena(n)})" for p, n in obligatorios)}
            if "dispara" not in se:                    # solo se recuerda, para los comandos que lo requieren
                self.registrar_externo(x)
                continue
            cmd = cmd_por_nombre[se["dispara"]]
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
                origen = next(((var, d[c["nombre"]]) for var, d in fuentes_ev if c["nombre"] in d), None)
                if origen is None:
                    args.append("null")
                elif origen[1]["opcional"] and not c["tipo"]["opcional"]:
                    args.append(f'({origen[0]}.{c["prop"]} ?? throw new DatoFaltante({cs_cadena(c["nombre"])}))')
                else:
                    args.append(f'{origen[0]}.{c["prop"]}')
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

    # ------------------------------------------------------------ mensajes que reciben los SA (G7)
    def preparar_mensajes_sa(self):
        """Lo que un sistema externo le envía a YateGear por un SA (YAML: recibe). Por cada SA, un receptor con un
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
                cmd = cmd_por_nombre[x["dispara"]]
                r = self.usar_raiz(cmd["raiz_nombre"])
                clase = self.tipo_cs_nuevo(nombres.pascal(nombre), f'mensaje "{nombre}" de "{msa["nombre"]}"')
                datos = self.campos(x.get("datos"), f'datos de "{nombre}" (YAML)')
                self.revisar_miembros(clase, [d["prop"] for d in datos])
                props, con = {d["nombre"]: d for d in datos}, x.get("con") or {}
                args = [] if cmd["crea"] else [f'mensaje.{r["id_prop"]}']
                for c in cmd["entrada_campos"]:
                    d = props.get(c["nombre"])
                    if c["nombre"] in con:
                        args.append(cs_literal(con[c["nombre"]], c["tipo"]))
                    elif d is None:
                        args.append("null")
                    elif d["tipo"]["opcional"] and not c["tipo"]["opcional"]:
                        args.append(f'(mensaje.{d["prop"]} ?? throw new DatoFaltante({cs_cadena(c["nombre"])}))')
                    else:
                        args.append(f'mensaje.{d["prop"]}')
                var_m = nombres.camel(cmd["nombre"])
                manejadores[var_m] = {"cs": cmd["manejador"], "var": var_m}
                obligatorios = ", ".join(f"({cs_cadena(nombres.camel(d['nombre']))}, {cs_cadena(d['nombre'])})"
                                         for d in datos if not d["tipo"]["opcional"])
                m = {"nombre": nombre, "clase": clase, "datos": datos, "datos_campos": datos, "comando": cmd["nombre"],
                     "comando_clase": cmd["clase"], "manejador_var": var_m, "args": args, "obligatorios": obligatorios,
                     "metodo": f"Recibir{clase}", "titulo": f'{msa["nombre"]}: {nombre}', "receptor": receptor,
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

    # ------------------------------------------------------------ escenarios
    def preparar_escenarios(self) -> list[dict]:
        """Cada escenario del YAML, con la llamada HTTP de cada paso, su identidad y lo esperado (de "espera").

        Cada paso trabaja con la raíz de su comando, consulta o evento (G2). Su identidad: un comando que crea la
        raíz la recibe (el siguiente consecutivo de esa raíz, que una solicitud rechazada no gasta, o la que se
        forma con sus datos); los demás pasos la toman de con, o si no, de la última identidad con el mismo nombre
        de dato en el escenario (regla de los datos: el calendario de un yate tiene la identidad del yate). Un
        evento de otro contexto con su propia identidad la toma de con.
        """
        cmd = {c["nombre"]: c for c in self.comandos}
        qs = {q["nombre"]: q for q in self.consultas}
        ext = {x["nombre"]: x for x in self.externos}
        msjs = {m["nombre"]: m for m in self.mensajes}
        escenarios, contador = [], {}
        # Coherencia (H-J5-02): las raíces que crean los pasos anteriores, en el orden en que corren (los escenarios
        # comparten la aplicación). Solo avisa: a veces repetir una identidad o usar una raíz inexistente es a propósito.
        creadas: dict[tuple, str] = {}
        self.avisos_escenarios = []
        for nombre_e, pasos in self.s["escenarios"].items():
            actual, primera, lista = {}, None, []
            for i, paso in enumerate(pasos, 1):
                nombre, op = (paso, {}) if isinstance(paso, str) else next(iter(paso.items()))
                op = op or {}
                con = op.get("con") or {}
                esp = op.get("espera")
                rechazo = isinstance(esp, int) or (isinstance(esp, dict) and "código" in esp)

                def cuerpo(campos, identidad=None, nombre_id=None):
                    b = {nombre_id: identidad} if identidad is not None else {}
                    for c in campos:
                        v = con[c["nombre"]] if c["nombre"] in con else None
                        b[nombres.camel(c["nombre"])] = valor_json(v, c["tipo"]) if c["nombre"] in con else ejemplo(c["nombre"], c["tipo"])
                    return b

                if nombre in cmd:
                    raiz_paso = cmd[nombre]["raiz_nombre"]
                elif nombre in msjs:
                    raiz_paso = cmd[msjs[nombre]["comando"]]["raiz_nombre"]
                elif nombre in qs:
                    raiz_paso = qs[nombre]["raiz_nombre"]
                else:
                    raiz_paso = cmd[ext[nombre]["comando"]]["raiz_nombre"] if ext[nombre]["comando"] else None
                r = self.usar_raiz(raiz_paso) if raiz_paso else None
                id_json = nombres.camel(r["id_nombre"]) if r else None
                previa = (con.get(r["id_nombre"]) or actual.get(r["id_nombre"])) if r else None
                ident = previa

                def identidad_al_crear(c, datos):
                    """La identidad que recibe la raíz que crea el comando c con este cuerpo (None si es un rechazo)."""
                    if r["consecutivo"]:
                        n_sig = contador.get(raiz_paso, 0) + 1
                        contador[raiz_paso] = n_sig - (1 if rechazo else 0)
                        return None if rechazo else r["prefijo"] + str(n_sig).zfill(r["digitos"])
                    valores = {**{k: valor_json(v, self.tipos_raiz[k]) for k, v in (c["spec"].get("valores") or {}).items()},
                               **{e["nombre"]: datos.get(nombres.camel(e["nombre"])) for e in c["entrada_campos"]}}
                    for g in c["spec"].get("guarda") or []:     # {campo: dato}: el campo vale lo que el dato
                        if isinstance(g, dict) and isinstance(next(iter(g.values())), str):
                            campo, dato = next(iter(g.items()))
                            if dato in valores:
                                valores.setdefault(campo, valores[dato])
                    faltan = [parte for parte in r["id_de"] if parte not in valores]
                    if faltan:
                        raise ErrorDeGeneracion(
                            f'escenario "{nombre_e}", paso {i}: la identidad que forma "{c["nombre"]}" usa '
                            f'{", ".join(chr(34) + x + chr(34) for x in faltan)}, que no sale de su entrada ni de sus valores '
                            f'(sale de un evento o de un servicio SA); los escenarios solo calculan la identidad con esos dos')
                    return "/".join(str(valores[parte]) for parte in r["id_de"])

                if nombre in msjs:                      # un mensaje de un SA (G7): como el comando que dispara
                    msj = msjs[nombre]
                    c = cmd[msj["comando"]]
                    tipo, metodo, crea = "mensaje de un servicio SA", "POST", c["crea"]
                    ruta = msj["ruta"].removeprefix(self.ruta_base)
                    datos = cuerpo(msj["datos_campos"])
                    if crea:
                        ident = identidad_al_crear(c, datos)
                        if not rechazo:
                            primera = primera or ident
                    else:
                        if r["id_nombre"] not in con and previa:
                            datos[id_json] = previa
                        ident = datos.get(id_json)
                elif nombre in cmd and cmd[nombre]["todas"]:   # sobre todas las raíces (G8): sin identidad
                    c = cmd[nombre]
                    tipo, metodo, crea = "comando", "POST", False
                    ruta, datos, ident = c["ruta"].removeprefix(self.ruta_base), cuerpo(c["entrada_campos"]), None
                elif nombre in cmd:
                    c = cmd[nombre]
                    tipo, metodo, ruta = "comando", "POST", c["ruta"].removeprefix(self.ruta_base)
                    crea = c["crea"]
                    if crea:
                        datos = cuerpo(c["entrada_campos"])
                        ident = identidad_al_crear(c, datos)
                        if not rechazo:
                            primera = primera or ident
                    else:
                        datos = cuerpo(c["entrada_campos"], ident, id_json)
                elif nombre in qs:
                    q = qs[nombre]
                    tipo, metodo, crea, datos = "consulta", "GET", False, None
                    ruta = q["ruta_prueba"] if q["todas"] else f'{q["ruta_prueba"]}/{ident}'
                    if q["todas"]:
                        ident = None
                    extra = cuerpo(q["entrada_campos"])
                    if extra:
                        ruta += "?" + "&".join(f"{a}={b}" for a, b in extra.items())
                else:
                    x = ext[nombre]
                    tipo, metodo, crea = "evento de otro contexto", "POST", False
                    ruta = x["ruta"].removeprefix(self.ruta_base)
                    if r and x["id_nombre"] == r["id_nombre"]:
                        datos = cuerpo(x["datos_campos"], ident, id_json)
                    else:                               # el evento llega con su propia identidad: sale de con
                        id_ev = con.get(x["id_nombre"], ejemplo(x["id_nombre"], tipos.interpretar("string")))
                        datos = cuerpo(x["datos_campos"], id_ev, nombres.camel(x["id_nombre"]))
                        if r:                           # la identidad de la raíz va en sus datos (G3)
                            if r["id_nombre"] not in con and previa:
                                datos[id_json] = previa
                            ident = datos.get(id_json)
                        else:
                            ident = None
                if r and ident:
                    clave, donde = (raiz_paso, ident), f'escenario "{nombre_e}", paso {i} ("{nombre}")'
                    espera_codigo = esp if isinstance(esp, int) else (esp.get("código") if isinstance(esp, dict) else None)
                    cmd_paso = cmd.get(nombre) or (cmd[msjs[nombre]["comando"]] if nombre in msjs else None)
                    crea_aqui = (cmd_paso is not None and (cmd_paso["crea"] or cmd_paso["si_no_existe"])) or \
                                (nombre in ext and ext[nombre]["comando"] and cmd[ext[nombre]["comando"]]["si_no_existe"])
                    if cmd_paso is not None and cmd_paso["crea"]:
                        if clave in creadas and espera_codigo != 409:
                            self.avisos_escenarios.append(f'{donde}: crea "{ident}", que ya creó {creadas[clave]}; '
                                                          "si se espera el rechazo, escribe espera: 409")
                    elif not crea_aqui and clave not in creadas and espera_codigo != 404:
                        self.avisos_escenarios.append(f'{donde}: usa "{ident}" ({raiz_paso}), que ningún paso anterior creó; '
                                                      "si se espera que no exista, escribe espera: 404")
                    if not rechazo:
                        creadas.setdefault(clave, donde)
                if r and ident and not rechazo:
                    actual[r["id_nombre"]] = ident
                if esp is None:
                    espera = {"tipo": "exito", "texto": "HTTP 2xx"}
                elif isinstance(esp, int):
                    espera = {"tipo": "codigo", "valor": esp, "texto": f"HTTP {esp}"}
                elif isinstance(esp, dict) and "código" in esp:   # rechazo con su motivo (campos de la respuesta)
                    campos_e = {specs.CAMPOS_DE_ERROR[k]: (nombres.pascal(v) if k == "estado actual" else v)
                                for k, v in esp.items() if k != "código"}
                    espera = {"tipo": "codigo", "valor": esp["código"], "campos": campos_e,
                              "texto": f'HTTP {esp["código"]} y ' + ", ".join(f"{k} = {v}" for k, v in esp.items() if k != "código")}
                elif isinstance(esp, str):
                    espera = {"tipo": "evento", "valor": esp, "texto": f'HTTP 2xx y el evento "{esp}"'}
                else:                                   # {dato de la salida: valor, ...}; en una lista, su número
                    tipos_salida = {s["nombre"]: s["tipo"] for s in qs[nombre]["salida_campos"]}
                    espera = {"tipo": "salida", "valores": {nombres.camel(k): valor_json(v, tipos_salida[k]) for k, v in esp.items()},
                              "texto": "HTTP 2xx y " + ", ".join(f'{k} = {v}' for k, v in esp.items())}
                lista.append({"numero": i, "nombre": nombre, "tipo": tipo, "crea": crea, "identidad": ident,
                              "metodo": metodo, "ruta": ruta, "cuerpo": datos, "espera": espera})
            escenarios.append({"nombre": nombre_e, "identidad": primera or "", "pasos": lista})
        return escenarios

    def pruebas_de_escenarios(self, escenarios: list[dict]) -> list[dict]:
        pruebas = []
        for k, e in enumerate(escenarios, 1):
            for p in e["pasos"]:
                pruebas.append({
                    "encabezado": f'Escenario {k}: {e["nombre"]} ({e["identidad"]})' if p["numero"] == 1 else None,
                    "titulo": f'{e["nombre"]} · paso {p["numero"]}: {p["nombre"]}',
                    "comentarios": [f'{p["tipo"].capitalize()}. Espera: {p["espera"]["texto"]}.'],
                    "metodo": p["metodo"], "ruta": p["ruta"],
                    "cuerpo": json.dumps(p["cuerpo"], ensure_ascii=False, indent=2) if p["cuerpo"] is not None else None})
        return pruebas

    # ------------------------------------------------------------ pruebas.http sin escenarios
    def preparar_pruebas(self) -> list[dict]:
        r = self.raiz
        cuenta = [0]

        def nueva_identidad():
            cuenta[0] += 1
            if not r["consecutivo"]:                    # se forma con los datos del comando que la crea
                return "{" + "/".join(r["id_de"]) + "}"
            return r["prefijo"] + str(cuenta[0]).zfill(r["digitos"])

        def cuerpo(cmd, identidad, cambios=None):
            b = {} if cmd["crea"] else {nombres.camel(r["id_nombre"]): identidad}
            for c in cmd["entrada_campos"]:
                b[nombres.camel(c["nombre"])] = ejemplo(c["nombre"], c["tipo"])
            for k, val in (cambios or {}).items():
                b[nombres.camel(k)] = val
            return json.dumps(b, ensure_ascii=False, indent=2)

        def llamada(cmd, identidad, nota, cambios=None):
            return {"titulo": f'{cmd["codigo"]} {cmd["nombre"]}', "comentarios": [nota], "metodo": "POST",
                    "ruta": cmd["ruta"].removeprefix(self.ruta_base), "cuerpo": cuerpo(cmd, identidad, cambios)}

        # Las llamadas siguen el orden del YAML, que es el orden del flujo; el resto del código va por nombre.
        pruebas = []
        en_yaml = list(self.s["comandos"])
        por_yaml = sorted(self.comandos, key=lambda c: en_yaml.index(c["nombre"]))
        crea = next(c for c in por_yaml if c["crea"])
        orden = [crea] + [c for c in por_yaml if not c["crea"]]
        principal = nueva_identidad()
        for c in orden:
            nota = f"Crea la raíz {principal}." if c["crea"] else f"Sobre {principal}."
            pruebas.append(llamada(c, principal, nota))
        q_yaml = list(self.s["consultas"])
        for q in sorted(self.consultas, key=lambda q: q_yaml.index(q["nombre"])):
            pruebas.append({"titulo": f'{q["codigo"]} {q["nombre"]}', "comentarios": [f"Sobre {principal}."], "metodo": "GET",
                            "ruta": f'{q["ruta_prueba"]}/{principal}', "cuerpo": None})
        bitacora = {"titulo": "Bitácora (infraestructura)", "metodo": "GET", "ruta": "/bitacora", "cuerpo": None,
                    "comentarios": ["Eventos publicados y llamadas a los servicios SA simulados, en orden."]}
        pruebas.append(bitacora)

        # Caminos alternativos: casos de los SA que usa el comando que crea, elegidos por su entrada.
        ent_crea = {c["nombre"] for c in crea["entrada_campos"]}
        con_casos = [c for c in orden if not c["crea"] and any(self.sas[s]["usa_casos"] for s in c["spec"].get("usa") or [])]
        for nombre_sa in crea["spec"].get("usa") or []:
            sa = self.sas[nombre_sa]
            for caso in sa["spec"].get("casos") or []:
                if not set(caso["si"]) <= ent_crea:
                    continue
                ident = nueva_identidad()
                cambios = {k: valor_json(vals[0], next(c["tipo"] for c in crea["entrada_campos"] if c["nombre"] == k))
                           for k, vals in caso["si"].items()}
                texto = ", ".join(f'{k} = {vals[0]}' for k, vals in caso["si"].items())
                pruebas.append(llamada(crea, ident, f'Camino alternativo: caso de "{nombre_sa}" con {texto}. Crea {ident}.', cambios))
                for c in con_casos:
                    pruebas.append(llamada(c, ident, f"Camino alternativo, sobre {ident}."))
                pruebas.append(bitacora)
        return pruebas

    # ------------------------------------------------------------ todo el contexto
    def generar(self) -> "Generador":
        """Prepara en memoria los archivos del contexto. Los escribe Solucion."""
        # Los objetos de valor del contexto se pueden usar como List<objeto de valor> en el YAML (G4).
        tipos.usar_objetos({v["nombre"]: {c["nombre"]: c for c in v["campos"]}
                            for a in self.ctx["agregados"] for v in a["objetos_valor"]})
        self.preparar_raiz()
        self.preparar_sas()
        self.preparar_eventos()
        self.preparar_comandos()
        self.preparar_consultas()
        self.preparar_politicas()
        self.preparar_eventos_externos()
        self.preparar_mensajes_sa()
        ctx, r = self.ctx, self.raiz
        cab_ctx = self.cabecera("ApplicationComponent", ctx["nombre"], ctx["id"])
        p = self.proyecto

        enums = sorted(self.enums.values(), key=lambda e: e["clase"])
        self.render("enums.g.cs.j2", f"{p}/Dominio/Enums.g.cs", enums=enums, cabecera=cab_ctx)
        self.render("infraestructura.g.cs.j2", f"{p}/Infraestructura/Infraestructura.g.cs", cabecera=cab_ctx)
        self.render("politicas.g.cs.j2", f"{p}/Politicas/Politicas.g.cs", politicas=self.politicas, cabecera=cab_ctx)
        self.render("registro.g.cs.j2", f"{p}/Registro.g.cs", cabecera=cab_ctx, contexto=ctx["nombre"],
                    raices=[x["raiz"] for x in self.raices.values()],
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

    def trazabilidad_csv(self) -> str:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["ID ArchiMate", "tipo", "nombre", "archivo generado", "clase"])
        for fila in sorted(set(self.traza)):
            w.writerow(fila)
        return buf.getvalue()


# ------------------------------------------------------------ solución

class Solucion:
    """Junta los contextos en una solución: host, bus entre contextos (Integracion), .sln y contextos.json."""

    def __init__(self, modelo: dict, specs_: list[dict], salida: Path):
        self.m, self.salida = modelo, salida
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
                      "ruta_base": g.ruta_base} for g in gs]
        h, i = self.host, INTEGRACION
        archivos[f"{h}/{h}.csproj"] = self.render("host.csproj.j2", cabecera=cab, contextos=contextos, integracion=i)
        archivos[f"{h}/Program.g.cs"] = self.render("host_program.g.cs.j2", cabecera=cab, contextos=contextos,
                                                     ns_integracion=ns_integracion)
        archivos[f"{h}/Properties/launchSettings.json"] = self.render("launchSettings.json.j2", proyecto=h)
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
        archivos["contextos.json"] = json.dumps(
            {"generado_desde": cab, "host": h, "puerto": PUERTO,
             "contextos": [{"nombre": g.ctx["nombre"], "proyecto": g.proyecto, "ruta_base": g.ruta_base,
                            "escenarios": g.escenarios_json, "trazabilidad": f"trazabilidad/{g.proyecto}.csv"}
                           for g in gs]}, ensure_ascii=False, indent=2) + "\n"
        for g in gs:
            for archivo in (f"{h}/Program.g.cs", f"{h}/{h}.csproj", sln, "global.json", "contextos.json"):
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


def main():
    for f in (sys.stdout, sys.stderr):
        f.reconfigure(encoding="utf-8")
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    ruta_json, ruta_salida, *rutas_yaml = sys.argv[1:]
    modelo = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
    specs_, errores = [], []
    for ruta_yaml in rutas_yaml:
        try:
            spec = specs.cargar_yaml(ruta_yaml)
        except Exception as e:                              # YAML mal escrito o clave repetida
            sys.exit(f"ERROR al leer {ruta_yaml}: {e}")
        rev = specs.Revisor(modelo, spec, ruta_yaml)
        rev.id_nombre = ""
        rev.revisar()
        errores += [f"{ruta_yaml}: {e}" for e in rev.errores]
        specs_.append(spec)
    if errores:
        print(f"Los YAML no cumplen con el modelo ({len(errores)} error(es)); no se generó nada:", file=sys.stderr)
        for e in errores:
            print("  ERROR", e, file=sys.stderr)
        sys.exit(1)
    try:
        res = Solucion(modelo, specs_, Path(ruta_salida)).generar()
    except (ErrorDeGeneracion, nombres.NombreInvalido) as e:
        sys.exit(f"ERROR de generación: {e}")
    generados = {n for n, _, _ in res["contextos"]}
    for ctx in modelo["contextos"]:
        if ctx["nombre"] not in generados:
            print(f'Sin YAML (no se genera): {ctx["nombre"]}')
    for nombre, proyecto, filas in res["contextos"]:
        print(f"Generado: {nombre} -> {proyecto} ({filas} filas de trazabilidad)")
    print(f"Archivos generados: {res['escritos']}")
    print(f"Manuales creados: {len(res['creados'])}; conservados sin tocar: {len(res['conservados'])}")
    for x in res["creados"]:
        print("  creado:", x)
    for x in res["borrados"]:
        print("  borrado (generado que ya no corresponde):", x)
    for x in res["huerfanos"]:
        print("  AVISO manual huérfano (no se borra ni se compila; revísalo):", x)
    for ctx_nombre, a in res["avisos_escenarios"]:
        print(f"  AVISO {ctx_nombre}, {a}")
    for x in res["sueltas"]:
        print(f"  AVISO {x}/ tiene código a mano de un contexto que ya no se genera (no se borra ni se compila; revísalo)")


if __name__ == "__main__":
    main()
