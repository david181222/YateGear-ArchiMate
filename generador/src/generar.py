"""Genera el proyecto C# de un contexto desde modelo-ddd.json y su YAML de especificaciones.

Capa 1: la estructura completa. Compila, corre y recorre el flujo, pero no valida
ni cambia estados; solo pone el estado inicial al crear la raíz (capa 2: Fase 5).

Primero revisa el YAML con specs.py; si hay errores, no genera nada.
Escribe:
  - los archivos generados (.g.cs y los de proyecto), siempre;
  - los archivos manuales (.cs), solo si no existen;
  - trazabilidad.csv.
Borra los .g.cs que ya no corresponden y avisa de los manuales huérfanos.

uso: python src/generar.py <modelo-ddd.json> <specs.yaml> <carpeta de salida>
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
INFRAESTRUCTURA = ("IRaiz", "IEvento", "Repositorio", "Bitacora", "RegistroDeBitacora", "BusDeEventos",
                   "RespuestaDeComando", "ReglaIncumplida", "NoEncontrado", "DatoFaltante", "Politicas", "Program",
                   "TransicionInvalida", "Estados", "EsperaDeEventos", "RespuestaDeEventoExterno",
                   "ReceptorDeEventosExternos")
MIEMBROS_RESERVADOS = {"Manejar", "ValidarReglas", "Publicar", "Llamar"}


class ErrorDeGeneracion(Exception):
    pass


# ------------------------------------------------------------ tipos y literales de C#

def cs_tipo(t: dict) -> str:
    base = nombres.pascal(t["enum"]["nombre"]) if t["base"] == "enum" else t["base"]
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
    return {"string": nombre, "int": 1, "decimal": 100, "bool": True,
            "DateOnly": "2026-02-01", "DateTime": "2026-02-01T09:00:00"}[b]


def valor_json(v, t: dict):
    """Un valor del YAML tal como viaja en JSON (los enum, con su nombre de C#)."""
    if t["base"] == "enum" and v is not None:
        return nombres.pascal(v)
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
        self.ns = f'{nombres.pascal(modelo["generado_desde"]["modelo_nombre"])}.{self.proyecto}'
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
        texto = self.env.get_template(plantilla).render(ns=self.ns, puerto=PUERTO, **datos)
        if "\r" in texto:
            raise ErrorDeGeneracion(f"{plantilla}: la salida tiene fin de línea CRLF")
        (self.manuales if manual else self.archivos)[destino] = texto

    # ------------------------------------------------------------ raíz y objetos de valor
    def preparar_raiz(self):
        ags = self.ctx["agregados"]
        if len(ags) != 1:
            raise ErrorDeGeneracion("el piloto genera un contexto con un solo agregado")
        ag = ags[0]
        if ag["entidades"]:
            raise ErrorDeGeneracion(f'"{ag["nombre"]}" tiene entidades; el generador todavía no las genera (se harán con Cobros y depósito)')
        r = ag["raiz"]
        sr = self.s["raices"][r["nombre"]]
        ident = sr["identidad"]
        clase = self.tipo_cs_nuevo(nombres.pascal(r["nombre"]), f'raíz "{r["nombre"]}"')
        estado_t = self.tipo(sr["estado"], f'estado de la raíz "{r["nombre"]}" (YAML)')
        var = nombres.camel(r["nombre"])
        raiz = {"id": r["id"], "nombre": r["nombre"], "clase": clase, "var": var, "agregado": ag,
                "id_nombre": ident["nombre"], "id_prop": nombres.pascal(ident["nombre"]),
                "prefijo": ident["prefijo"], "digitos": ident["digitos"],
                "estado_t": estado_t, "estado_clase": cs_tipo(estado_t), "campos": [], "vos": []}
        fuentes = {ident["nombre"]: fuente(f'{var}.{raiz["id_prop"]}', {**tipos.interpretar("string")}),
                   "estado": fuente(f"{var}.Estado", estado_t)}
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
        self.vos = {}
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
            self.vos[v["nombre"]] = vo
            for c in campos:
                if card == "Uno":
                    fuentes.setdefault(c["nombre"], fuente(f"{var}.{prop}.{c['prop']}", c["tipo"]))
                elif card == "Cero o uno":       # si se pide obligatorio y no hay objeto de valor, DatoFaltante
                    fuentes.setdefault(c["nombre"], fuente(
                        f'({var}.{prop} ?? throw new DatoFaltante({cs_cadena(v["nombre"])})).{c["prop"]}', c["tipo"],
                        f"{var}.{prop}?.{c['prop']}"))
        self.revisar_miembros(clase, [raiz["id_prop"], "Estado"] + [c["prop"] for c in raiz["campos"]] + [v["prop"] for v in raiz["vos"]])
        self.raiz, self.fuentes_raiz = raiz, fuentes

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
        r = self.raiz
        self.eventos = {}
        publica = {}
        for c in self.ctx["comandos"]:
            for e in c["eventos"]:
                publica.setdefault(e, []).append(f'"{c["nombre"]}" ({c["codigo"]})')
        for me in self.ctx["eventos"]:
            se = self.s["eventos"][me["nombre"]]
            clase = self.tipo_cs_nuevo(nombres.pascal(me["nombre"]), f'evento "{me["nombre"]}"')
            datos = self.campos(se.get("datos"), f'datos del evento "{me["nombre"]}" (YAML)')
            calc = self.campos(se.get("calculados"), f'calculados del evento "{me["nombre"]}" (YAML)')
            params = [{"cs": "string", "prop": r["id_prop"]}] + datos + calc
            self.revisar_miembros(clase, [p["prop"] for p in params] + ["NombreEnElModelo", "Identidad"])
            ev = {"id": me["id"], "nombre": me["nombre"], "clase": clase, "datos": datos, "calculados": calc,
                  "parametros": params, "publicado_por": ", ".join(publica.get(me["id"], []))}
            self.eventos[me["nombre"]] = ev
            archivo = f"{self.proyecto}/Eventos/{clase}.g.cs"
            self.render("evento.g.cs.j2", archivo, e=ev, raiz=r,
                        cabecera=self.cabecera("ApplicationEvent", me["nombre"], me["id"]))
            self.traza_de(me["id"], "ApplicationEvent", me["nombre"], archivo, clase)

    # ------------------------------------------------------------ comandos
    def preparar_comandos(self):
        r, v = self.raiz, self.raiz["var"]
        self.comandos = []
        ev_por_id = {e["id"]: e["nombre"] for e in self.ctx["eventos"]}
        for mc in self.ctx["comandos"]:
            sc = self.s["comandos"][mc["nombre"]]
            clase = nombres.pascal(mc["nombre"])
            n = {k: self.tipo_cs_nuevo(x, f'comando "{mc["nombre"]}"') for k, x in
                 {"clase": clase, "datos": f"{clase}Datos", "manejador": f"{clase}Manejador"}.items()}
            crea = sc.get("crea", False)

            def estado(nombre_estado):                # literal de C# de un estado de la raíz
                return f'{r["estado_clase"]}.{nombres.pascal(nombre_estado)}'

            ent = self.campos(sc.get("entrada"), f'entrada de "{mc["nombre"]}" (YAML)')
            params = ([] if crea else [{"cs": "string", "prop": r["id_prop"]}]) + ent
            self.revisar_miembros(clase, [p["prop"] for p in params])
            capa_ent = {c["nombre"]: fuente(f'comando.{c["prop"]}', c["tipo"]) for c in ent}

            antes = Ambito()                       # antes de guardar
            if not crea:
                antes.agregar(dict(self.fuentes_raiz))
            antes.agregar(capa_ent)
            llamadas, deps, datos_props, datos_args = [], [], [], ["comando"]
            datos_props.append({"cs": clase, "prop": "Comando"})
            if not crea:
                datos_props.append({"cs": r["clase"], "prop": r["clase"]})
                datos_args.append(v)
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

            # Lo que guarda (después de ValidarReglas).
            asignaciones = []
            if crea:
                asignaciones.append({"prop": "Estado", "expr": f'{r["estado_clase"]}.{nombres.pascal(sc["a"])}'})
            for g in sc.get("guarda") or []:
                if g in self.vos:
                    vo = self.vos[g]
                    args = []
                    for c in vo["campos"]:
                        args.append(antes.expr(c["nombre"], c["tipo"]["opcional"]) if antes.buscar(c["nombre"]) else "null")
                    asignaciones.append({"prop": vo["prop"], "expr": f'new {vo["clase"]}({", ".join(args)})'})
                else:
                    c = next(x for x in r["campos"] if x["nombre"] == g)
                    t = tipos.interpretar(c["tipo_yaml"])
                    asignaciones.append({"prop": c["prop"], "expr": antes.expr(g, t["opcional"])})

            # Eventos (después de guardar: ya hay raíz e identidad).
            despues = Ambito()
            despues.agregar(dict(self.fuentes_raiz))
            despues.agregar(capa_ent)
            for capa in capas_sa:
                despues.agregar(capa)
            calculados, vistos = [], set()
            publicar = {}
            for nombre_ev in eventos_cmd:
                ev = self.eventos[nombre_ev]
                args = [f'{v}.{r["id_prop"]}']
                args += [despues.expr(d["nombre"], d["tipo"]["opcional"]) for d in ev["datos"]]
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
                   "operacion": cs_cadena(mc["nombre"]),
                   "desde": [] if crea else [estado(x) for x in sc.get("desde") or []],
                   "a": estado(sc["a"]) if sc.get("a") and not crea else None,
                   "resultados_con_desde": [x for x in resultados if x["desde"]],
                   "resultados_con_a": [x for x in resultados if x["a"]],
                   "sin_resultado": cs_cadena(f'Ningún resultado de "{mc["nombre"]}" se cumple con estos datos.'),
                   "escribe": crea or mc["acceso"] in ("escritura", "lectura y escritura"),
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
            self.render("comando_manual.cs.j2", com["manual"], manual=True, c=com, cabecera=cab)
            for x in ("clase", "datos", "manejador"):
                self.traza_de(mc["id"], "ApplicationProcess", mc["nombre"], com["archivo"], n[x])
            self.traza_de(mc["id"], "ApplicationProcess", mc["nombre"], com["manual"], f'{n["manejador"]} (manual)')
            self.traza_de(mc["id"], "ApplicationProcess", mc["nombre"], f"{self.proyecto}/Program.g.cs", f'POST {com["ruta"]}')
            if mc["acceso_id"]:
                self.traza_de(mc["acceso_id"], "Access", f'{mc["nombre"]} -> {r["nombre"]} ({mc["acceso"]})', com["archivo"], n["manejador"])
            for lt in mc["lee_tambien"]:
                self.traza_de(lt["acceso_id"], "Access", f'{mc["nombre"]} -> otra raíz (lectura)', com["archivo"], n["manejador"])
            self.traza_de(mc["servicio_negocio"]["id"], "BusinessService", mc["servicio_negocio"]["nombre"], com["archivo"], n["manejador"])
            self.traza_de(k["id"], "Contract", k["nombre"], com["archivo"], n["manejador"])
            self.traza_de(k["id"], "Contract", k["nombre"], com["manual"], f'{n["manejador"]}.ValidarReglas (manual)')

    # ------------------------------------------------------------ consultas
    def preparar_consultas(self):
        r, v = self.raiz, self.raiz["var"]
        self.consultas = []
        for mq in self.ctx["consultas"]:
            sq = self.s["consultas"][mq["nombre"]]
            clase = nombres.pascal(mq["nombre"])
            n = {k: self.tipo_cs_nuevo(x, f'consulta "{mq["nombre"]}"') for k, x in
                 {"clase": clase, "salida": f"{clase}Salida", "datos": f"{clase}Datos", "manejador": f"{clase}Manejador"}.items()}
            ent = self.campos(sq.get("entrada"), f'entrada de "{mq["nombre"]}" (YAML)')
            params = [{"cs": "string", "prop": r["id_prop"]}] + ent
            self.revisar_miembros(clase, [p["prop"] for p in params])
            amb = Ambito()
            amb.agregar(dict(self.fuentes_raiz))
            amb.agregar({c["nombre"]: fuente(f'consulta.{c["prop"]}', c["tipo"]) for c in ent})
            salida = []
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
            lambda_params = [f"string {id_param}"] + [f'{c["cs"]} {nombres.camel(c["nombre"])}' for c in ent]
            args = [id_param] + [nombres.camel(c["nombre"]) for c in ent]
            k = mq["contrato"]
            q = {**n, "nombre": mq["nombre"], "codigo": mq["codigo"], "id": mq["id"], "parametros": params,
                 "salida_campos": salida, "calculados": calculados, "contrato": k, "servicio_negocio": mq["servicio_negocio"],
                 "reglas": lineas(k["reglas"]) if k["reglas"] else ["El contrato no tiene reglas."],
                 "salida_contrato": lineas(k["salida"]),
                 "ruta": f'{self.ruta_base}/consultas/{nombres.ruta(mq["nombre"])}/{{{id_param}}}',
                 "ruta_prueba": f'/consultas/{nombres.ruta(mq["nombre"])}',
                 "lambda_params": ", ".join(lambda_params), "args": ", ".join(args),
                 "archivo": f'{self.proyecto}/Consultas/{clase}.g.cs', "manual": f'{self.proyecto}/Consultas/{clase}.cs',
                 "entrada_campos": ent}
            self.consultas.append(q)
            cab = self.cabecera("ApplicationService", mq["nombre"], mq["id"], mq["codigo"])
            self.render("consulta.g.cs.j2", q["archivo"], q=q, raiz=r, cabecera=cab)
            self.render("consulta_manual.cs.j2", q["manual"], manual=True, q=q, cabecera=cab)
            for x in ("clase", "salida", "datos", "manejador"):
                self.traza_de(mq["id"], "ApplicationService", mq["nombre"], q["archivo"], n[x])
            self.traza_de(mq["id"], "ApplicationService", mq["nombre"], q["manual"], f'{n["manejador"]} (manual)')
            self.traza_de(mq["id"], "ApplicationService", mq["nombre"], f"{self.proyecto}/Program.g.cs", f'GET {q["ruta"]}')
            for lee in mq["lee"]:
                self.traza_de(lee["acceso_id"], "Access", f'{mq["nombre"]} -> {r["nombre"]} (lectura)', q["archivo"], n["manejador"])
            self.traza_de(mq["servicio_negocio"]["id"], "BusinessService", mq["servicio_negocio"]["nombre"], q["archivo"], n["manejador"])
            self.traza_de(k["id"], "Contract", k["nombre"], q["archivo"], n["manejador"])
            self.traza_de(k["id"], "Contract", k["nombre"], q["manual"], f'{n["manejador"]}.ValidarReglas (manual)')

    # ------------------------------------------------------------ políticas
    def preparar_politicas(self):
        r = self.raiz
        ev_por_id = {e["id"]: e["nombre"] for e in self.ctx["eventos"]}
        cmd_por_id = {c["id"]: c for c in self.comandos}
        self.politicas = []
        for p in self.ctx["politicas"]:
            ev = self.eventos[ev_por_id[p["evento_id"]]]
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
        r = self.raiz
        catalogo = {(o["nombre"], e["nombre"]): e["id"] for o in self.ctx["otros_contextos"] for e in o["eventos"]}
        cmd_por_nombre = {c["nombre"]: c for c in self.comandos}
        ext = self.s.get("eventos_de_otros_contextos") or {}
        clases = {n: nombres.pascal(n) for n in ext}
        self.externos, manejadores = [], {}
        for nombre in sorted(ext):
            se = ext[nombre]
            clase = self.tipo_cs_nuevo(clases[nombre], f'evento de otro contexto "{nombre}"')
            datos = self.campos(se.get("datos"), f'datos de "{nombre}" (YAML)')
            params = [{"cs": "string", "prop": r["id_prop"]}] + datos
            self.revisar_miembros(clase, [p["prop"] for p in params] + ["NombreEnElModelo", "Identidad"])
            cmd = cmd_por_nombre[se["dispara"]]
            junto = list(se.get("junto_con") or [])
            grupo = sorted([nombre] + junto)
            # De dónde sale cada dato de la entrada del comando: con (fijo) o un evento del grupo, por nombre.
            variables = [{"var": nombres.camel(g), "clase": clases[g], "nombre": cs_cadena(g)} for g in grupo] if junto else []
            fuentes_ev = [(nombres.camel(g) if junto else "evento", {k: tipos.interpretar(t) for k, t in (ext[g].get("datos") or {}).items()})
                          for g in (grupo if junto else [nombre])]
            con = se.get("con") or {}
            args = [f'evento.{r["id_prop"]}']
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
            x = {"nombre": nombre, "clase": clase, "id": catalogo[(se["de"], nombre)], "de": se["de"],
                 "parametros": params, "comando": cmd["nombre"], "comando_clase": cmd["clase"], "manejador_var": var_m,
                 "junto_con": junto, "grupo": [cs_cadena(g) for g in grupo] if junto else [],
                 "grupo_nombre": cs_cadena(cmd["nombre"]), "variables": variables, "args": args,
                 "ruta": f'{self.ruta_base}/eventos-externos/{nombres.ruta(nombre)}',
                 "datos_campos": datos}
            self.externos.append(x)
            archivo = f"{self.proyecto}/EventosExternos/{clase}.g.cs"
            self.render("evento_externo.g.cs.j2", archivo, x=x, raiz=r,
                        cabecera=self.cabecera("ApplicationEvent", nombre, x["id"]))
            receptor = f"{self.proyecto}/EventosExternos/ReceptorDeEventosExternos.g.cs"
            self.traza_de(x["id"], "ApplicationEvent", nombre, archivo, clase)
            self.traza_de(x["id"], "ApplicationEvent", nombre, receptor, "ReceptorDeEventosExternos")
            self.traza_de(x["id"], "ApplicationEvent", nombre, f"{self.proyecto}/Program.g.cs", f'POST {x["ruta"]}')
        if self.externos:
            ctx = self.ctx
            self.render("receptor.g.cs.j2", f"{self.proyecto}/EventosExternos/ReceptorDeEventosExternos.g.cs",
                        externos=self.externos, manejadores=[manejadores[k] for k in sorted(manejadores)],
                        cabecera=self.cabecera("ApplicationComponent", ctx["nombre"], ctx["id"]))

    # ------------------------------------------------------------ escenarios
    def preparar_escenarios(self) -> list[dict]:
        """Cada escenario del YAML, con la llamada HTTP de cada paso y lo esperado (de "espera")."""
        r = self.raiz
        cmd = {c["nombre"]: c for c in self.comandos}
        qs = {q["nombre"]: q for q in self.consultas}
        ext = {x["nombre"]: x for x in self.externos}
        id_json = nombres.camel(r["id_nombre"])
        escenarios = []
        for k, (nombre_e, pasos) in enumerate(self.s["escenarios"].items(), 1):
            ident = r["prefijo"] + str(k).zfill(r["digitos"])
            lista = []
            for i, paso in enumerate(pasos, 1):
                nombre, op = (paso, {}) if isinstance(paso, str) else next(iter(paso.items()))
                op = op or {}
                con = op.get("con") or {}

                def cuerpo(campos, con_identidad=True):
                    b = {id_json: ident} if con_identidad else {}
                    for c in campos:
                        v = con[c["nombre"]] if c["nombre"] in con else None
                        b[nombres.camel(c["nombre"])] = valor_json(v, c["tipo"]) if c["nombre"] in con else ejemplo(c["nombre"], c["tipo"])
                    return b

                if nombre in cmd:
                    c = cmd[nombre]
                    tipo, metodo, ruta = "comando", "POST", c["ruta"].removeprefix(self.ruta_base)
                    datos, crea = cuerpo(c["entrada_campos"], not c["crea"]), c["crea"]
                elif nombre in qs:
                    q = qs[nombre]
                    tipo, metodo, crea, datos = "consulta", "GET", False, None
                    ruta = f'{q["ruta_prueba"]}/{ident}'
                    extra = cuerpo(q["entrada_campos"], False)
                    if extra:
                        ruta += "?" + "&".join(f"{a}={b}" for a, b in extra.items())
                else:
                    x = ext[nombre]
                    tipo, metodo, crea = "evento de otro contexto", "POST", False
                    ruta, datos = x["ruta"].removeprefix(self.ruta_base), cuerpo(x["datos_campos"])
                esp = op.get("espera")
                if esp is None:
                    espera = {"tipo": "exito", "texto": "HTTP 2xx"}
                elif isinstance(esp, int):
                    espera = {"tipo": "codigo", "valor": esp, "texto": f"HTTP {esp}"}
                elif isinstance(esp, str):
                    espera = {"tipo": "evento", "valor": esp, "texto": f'HTTP 2xx y el evento "{esp}"'}
                else:
                    espera = {"tipo": "estado", "valor": esp["estado"], "json": nombres.pascal(esp["estado"]),
                              "texto": f'HTTP 2xx y estado "{esp["estado"]}"'}
                lista.append({"numero": i, "nombre": nombre, "tipo": tipo, "crea": crea, "metodo": metodo,
                              "ruta": ruta, "cuerpo": datos, "espera": espera})
            escenarios.append({"nombre": nombre_e, "identidad": ident, "pasos": lista})
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
            nota = f"Crea el arriendo {principal}." if c["crea"] else f"Sobre {principal}."
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

    # ------------------------------------------------------------ todo
    def generar(self) -> dict:
        self.preparar_raiz()
        self.preparar_sas()
        self.preparar_eventos()
        self.preparar_comandos()
        self.preparar_consultas()
        self.preparar_politicas()
        self.preparar_eventos_externos()
        ctx, r = self.ctx, self.raiz
        cab_ctx = self.cabecera("ApplicationComponent", ctx["nombre"], ctx["id"])
        p = self.proyecto

        enums = sorted(self.enums.values(), key=lambda e: e["clase"])
        self.render("enums.g.cs.j2", f"{p}/Dominio/Enums.g.cs", enums=enums, cabecera=cab_ctx)
        self.render("infraestructura.g.cs.j2", f"{p}/Infraestructura/Infraestructura.g.cs", cabecera=cab_ctx)
        self.render("politicas.g.cs.j2", f"{p}/Politicas/Politicas.g.cs", politicas=self.politicas, cabecera=cab_ctx)
        self.render("program.g.cs.j2", f"{p}/Program.g.cs", cabecera=cab_ctx, raiz=r, sas=list(self.sas.values()),
                    comandos=self.comandos, consultas=self.consultas, externos=self.externos, ruta_base=self.ruta_base)
        self.render("launchSettings.json.j2", f"{p}/Properties/launchSettings.json", proyecto=p)
        self.render("global.json.j2", "global.json")
        guid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'archimate:{ctx["id"]}')).upper()
        self.render("solucion.sln.j2", f'{nombres.pascal(self.m["generado_desde"]["modelo_nombre"])}.sln',
                    proyecto=p, guid=guid, tipo_proyecto=TIPO_PROYECTO_CS,
                    cabecera=self.cabecera("Model", self.m["generado_desde"]["modelo_nombre"], self.m["generado_desde"]["modelo_id"]))
        if self.s.get("escenarios"):
            escenarios = self.preparar_escenarios()
            pruebas = self.pruebas_de_escenarios(escenarios)
            self.archivos["escenarios.json"] = json.dumps(
                {"generado_desde": self.cabecera("ApplicationComponent", ctx["nombre"], ctx["id"]),
                 "ruta_base": self.ruta_base, "escenarios": escenarios}, ensure_ascii=False, indent=2) + "\n"
            self.traza_de(ctx["id"], "ApplicationComponent", ctx["nombre"], "escenarios.json", "")
        else:
            escenarios, pruebas = [], self.preparar_pruebas()
        self.render("pruebas.http.j2", "pruebas.http", cabecera=cab_ctx, ruta_base=self.ruta_base, pruebas=pruebas,
                    con_escenarios=bool(escenarios), primero=r["prefijo"] + "1".zfill(r["digitos"]))
        for archivo, clase in [(f"{p}/{p}.csproj", ""), (f"{p}/Program.g.cs", "Program"),
                               (f"{p}/Infraestructura/Infraestructura.g.cs", "infraestructura"),
                               (f"{p}/Dominio/Enums.g.cs", "enums"), (f"{p}/Properties/launchSettings.json", ""),
                               ("global.json", ""), (f'{nombres.pascal(self.m["generado_desde"]["modelo_nombre"])}.sln', ""),
                               ("pruebas.http", "")]:
            self.traza_de(ctx["id"], "ApplicationComponent", ctx["nombre"], archivo, clase)

        # Manuales huérfanos: un .cs manual sin su .g.cs. No se borran; se sacan de la compilación.
        huerfanos = []
        for carpeta in CARPETAS_MANUALES:
            d = self.salida / p / carpeta
            if d.is_dir():
                for f in sorted(d.glob("*.cs")):
                    if f.name.endswith(".g.cs"):
                        continue
                    rel = f"{p}/{carpeta}/{f.name}"
                    if f"{p}/{carpeta}/{f.stem}.g.cs" not in self.archivos:
                        huerfanos.append(rel)
        self.render("proyecto.csproj.j2", f"{p}/{p}.csproj", cabecera=cab_ctx,
                    huerfanos=[{"ruta": h.removeprefix(f"{p}/").replace("/", "\\"),
                                "falta": h.removeprefix(f"{p}/").removesuffix(".cs").replace("/", "\\") + ".g.cs"}
                               for h in huerfanos])

        # Escribir.
        escritos, creados, conservados, borrados = 0, [], [], []
        for rel, texto in sorted(self.archivos.items()):
            destino = self.salida / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(texto.encode("utf-8"))
            escritos += 1
        for rel, texto in sorted(self.manuales.items()):
            destino = self.salida / rel
            if destino.exists():
                conservados.append(rel)
            else:
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(texto.encode("utf-8"))
                creados.append(rel)
        for f in sorted((self.salida / p).rglob("*.g.cs")):
            rel = f.relative_to(self.salida).as_posix()
            if rel.split("/")[1] in ("bin", "obj"):
                continue
            if rel not in self.archivos:
                f.unlink()
                borrados.append(rel)
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["ID ArchiMate", "tipo", "nombre", "archivo generado", "clase"])
        for fila in sorted(set(self.traza)):
            w.writerow(fila)
        (self.salida / "trazabilidad.csv").write_bytes(buf.getvalue().encode("utf-8"))
        return {"escritos": escritos, "creados": creados, "conservados": conservados, "borrados": borrados,
                "huerfanos": huerfanos, "filas_traza": len(set(self.traza))}


def main():
    for f in (sys.stdout, sys.stderr):
        f.reconfigure(encoding="utf-8")
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    ruta_json, ruta_yaml, ruta_salida = sys.argv[1:]
    modelo = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
    try:
        spec = specs.cargar_yaml(ruta_yaml)
    except Exception as e:                                  # YAML mal escrito o clave repetida
        sys.exit(f"ERROR al leer {ruta_yaml}: {e}")
    rev = specs.Revisor(modelo, spec, ruta_yaml)
    rev.id_nombre = ""
    rev.revisar()
    if rev.errores:
        print(f"El YAML no cumple con el modelo ({len(rev.errores)} error(es)); no se generó nada:", file=sys.stderr)
        for e in rev.errores:
            print("  ERROR", e, file=sys.stderr)
        sys.exit(1)
    try:
        res = Generador(modelo, spec, Path(ruta_salida)).generar()
    except (ErrorDeGeneracion, nombres.NombreInvalido) as e:
        sys.exit(f"ERROR de generación: {e}")
    print(f"Archivos generados: {res['escritos']}; filas de trazabilidad: {res['filas_traza']}")
    print(f"Manuales creados: {len(res['creados'])}; conservados sin tocar: {len(res['conservados'])}")
    for x in res["creados"]:
        print("  creado:", x)
    for x in res["borrados"]:
        print("  borrado (.g.cs que ya no corresponde):", x)
    for x in res["huerfanos"]:
        print("  AVISO manual huérfano (no se borra ni se compila; revísalo):", x)


if __name__ == "__main__":
    main()
