"""Extrae los contextos del modelo ArchiMate y escribe modelo-ddd.json.

Todo se busca por tipo y por relación del modelo, nunca por nombre. Un contexto es
un componente de aplicación al que se le asigna al menos un proceso de aplicación
con la propiedad "Código del servicio" (o "Servicio básico V4", el nombre que usa el modelo
de YateGear). Nunca se leen los anidamientos de las vistas.

Sin nombres de contexto, extrae todos. Con nombres, solo esos (los demás quedan
como "otros_contextos" de cada uno, igual que siempre).

Si una validación falla, junta todos los errores, los muestra y termina con
código 1 sin escribir el JSON.

uso: python src/extraer.py <modelo.xml | modelo.archimate> <salida.json> ["<Contexto ...>" ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import leer
import tipos

CARDINALIDADES = ("Uno", "Cero o uno", "Muchos")
PREFIJO_AGREGADO = "Agregado "
PREFIJO_CAMPO = "Campo: "
# El código de un comando, una consulta o un servicio SA. Se acepta el nombre neutro (el recomendado) o el que usa el
# modelo de YateGear, que viene de su vista V4 ("Descomposición de servicios"). El valor es libre (SB-03, PR-1, ...), pero
# no se repite en el modelo y es el mismo en el servicio de negocio (Código) y en el contrato (Servicio).
P_CODIGO_SB = ("Código del servicio", "Servicio básico V4")
P_CODIGO_SA = ("Código del servicio anticorrupción", "Servicio anticorrupción V4")
NOMBRE_SB = '"Código del servicio" (o "Servicio básico V4")'
NOMBRE_SA = '"Código del servicio anticorrupción" (o "Servicio anticorrupción V4")'
P_TIPO_DDD = "Tipo DDD"


class Extractor:
    def __init__(self, g: leer.Grafo):
        self.g = g
        self.errores: list[str] = []
        self.avisos: list[str] = []
        self.codigos_dobles: set[str] = set()

    # ------------------------------------------------------------ utilidades
    def c(self, i: str) -> leer.Concepto:
        return self.g.conceptos[i]

    def ref(self, i: str) -> str:
        x = self.c(i)
        return f'{x.tipo} "{x.nombre}" ({x.id})'

    def codigo(self, i: str, claves: tuple[str, ...]) -> str | None:
        """El código del elemento: el valor de la propiedad de claves que tenga (neutra o la de YateGear). Si tiene las dos
        con valores distintos, es un error (se informa una vez)."""
        valores = {k: self.c(i).prop(k) for k in claves if self.c(i).prop(k)}
        if len(set(valores.values())) > 1 and i not in self.codigos_dobles:
            self.codigos_dobles.add(i)
            self.error("código", f"{self.ref(i)} tiene " + " y ".join(f'"{k}" = {v}' for k, v in valores.items())
                       + ": deja una sola")
        return next(iter(valores.values()), None)

    def error(self, regla: str, texto: str):
        self.errores.append(f"[{regla}] {texto}")

    def aviso(self, texto: str):
        self.avisos.append(texto)

    def salen(self, i, tipo_rel, tipo_destino=None):
        return [r for r in self.g.salen[i] if r.tipo == tipo_rel
                and (tipo_destino is None or self.c(r.destino).tipo == tipo_destino)]

    def llegan(self, i, tipo_rel, tipo_origen=None):
        return [r for r in self.g.llegan[i] if r.tipo == tipo_rel
                and (tipo_origen is None or self.c(r.origen).tipo == tipo_origen)]

    @staticmethod
    def por_nombre(ids, g):
        return sorted(ids, key=lambda i: (g.conceptos[i].nombre, i))

    # ------------------------------------------------------------ piezas
    def campos(self, i: str) -> list[dict]:
        """Propiedades "Campo: <nombre>" en el orden del modelo, con su tipo interpretado."""
        out = []
        for clave, valor in self.c(i).propiedades:
            if not clave.startswith(PREFIJO_CAMPO):
                continue
            nombre = clave[len(PREFIJO_CAMPO):].strip()
            if not nombre:
                self.error("campo", f'propiedad "{clave}" sin nombre de campo en {self.ref(i)}')
                continue
            try:
                t = tipos.interpretar(valor)
            except tipos.TipoInvalido as e:
                self.error("tipo de campo", f'campo "{nombre}" de {self.ref(i)}: {e}')
                continue
            out.append({"nombre": nombre, **t})
        return out

    def contrato(self, servicio_app: str, codigo: str) -> tuple[dict | None, dict | None]:
        """Servicio de aplicación o comando -> realiza -> servicio de negocio -> asociación -> contrato."""
        sn = [r.destino for r in self.salen(servicio_app, "Realization", "BusinessService")
              if self.c(r.destino).prop("Código") == codigo]
        if len(sn) != 1:
            self.error("contrato", f"{self.ref(servicio_app)} debe realizar 1 servicio de negocio con Código = {codigo}; tiene {len(sn)}")
            return None, None
        sn = sn[0]
        asociados = [r.origen if r.destino == sn else r.destino
                     for r in self.g.salen[sn] + self.g.llegan[sn] if r.tipo == "Association"]
        contratos = [i for i in asociados if self.c(i).tipo == "Contract"]
        if len(contratos) != 1:
            self.error("contrato", f"{self.ref(sn)} debe tener 1 contrato asociado; tiene {len(contratos)}")
            return {"id": sn, "nombre": self.c(sn).nombre}, None
        k = self.c(contratos[0])
        if k.prop("Servicio") != codigo:
            self.error("contrato", f'{self.ref(k.id)} tiene Servicio = {k.prop("Servicio")} y se esperaba {codigo}')
        partes = {"Entrada": [], "Salida": [], "Reglas": []}
        actual = None
        for linea in k.documentacion.split("\n"):
            cab = next((p for p in partes if linea.startswith(p + ":")), None)
            if cab:
                actual = cab
                linea = linea[len(cab) + 1:]
            if actual:
                partes[actual].append(linea.strip())
        texto = {p: "\n".join(v).strip() for p, v in partes.items()}
        for p in ("Entrada", "Salida"):
            if not texto[p]:
                self.error("contrato", f'{self.ref(k.id)} no tiene la línea "{p}:"')
        return ({"id": sn, "nombre": self.c(sn).nombre},
                {"id": k.id, "nombre": k.nombre, "entrada": texto["Entrada"],
                 "salida": texto["Salida"], "reglas": texto["Reglas"]})

    def contextos(self) -> list[str]:
        """Nombres de los contextos del modelo, por orden alfabético."""
        return sorted({c.nombre for c in self.g.elementos("ApplicationComponent")
                       if any(self.codigo(r.destino, P_CODIGO_SB)
                              for r in self.salen(c.id, "Assignment", "ApplicationProcess"))})

    # ------------------------------------------------------------ contexto
    def extraer(self, nombre_ctx: str) -> dict | None:
        g = self.g
        ctxs = [c for c in g.elementos("ApplicationComponent") if c.nombre == nombre_ctx]
        if len(ctxs) != 1:
            self.error("contexto", f'debe haber 1 componente de aplicación "{nombre_ctx}"; hay {len(ctxs)}')
            return None
        ctx = ctxs[0].id

        # Comandos: asignación contexto -> proceso de aplicación.
        comandos = [r.destino for r in self.salen(ctx, "Assignment", "ApplicationProcess")]
        for i in comandos:
            if not self.codigo(i, P_CODIGO_SB):
                self.error("comando", f"{self.ref(i)} está asignado al contexto pero no tiene la propiedad {NOMBRE_SB}")
        # Consultas: realización contexto -> servicio de aplicación con código SB.
        consultas = [r.destino for r in self.salen(ctx, "Realization", "ApplicationService")
                     if self.codigo(r.destino, P_CODIGO_SB)]
        # Servicios SA: servicio (relación) SA -> contexto.
        sas = [r.origen for r in self.llegan(ctx, "Serving", "ApplicationService")
               if self.codigo(r.origen, P_CODIGO_SA)]

        # Agregados: los "Agregado ..." que agregan los comandos del contexto (las agrupaciones de la V11 no cuentan).
        agrupaciones_agr = {c.id for c in g.elementos("Grouping") if c.nombre.startswith(PREFIJO_AGREGADO)}
        agregado_de = {}
        for i in comandos:
            ags = [r.origen for r in self.llegan(i, "Aggregation", "Grouping") if r.origen in agrupaciones_agr]
            if len(ags) != 1:
                self.error("agregado", f"{self.ref(i)} debe estar en 1 agrupación \"{PREFIJO_AGREGADO}...\"; está en {len(ags)}")
            else:
                agregado_de[i] = ags[0]
        agregados = self.por_nombre(set(agregado_de.values()), g)

        raiz_de, agregados_json, enums = {}, [], {}
        for ag in agregados:
            contenido = [r.destino for r in self.salen(ag, "Aggregation")]
            raices = [i for i in contenido if self.c(i).tipo == "DataObject" and self.c(i).prop(P_TIPO_DDD) == "Raíz"]
            if len(raices) != 1:
                self.error("agregado", f"{self.ref(ag)} debe agregar exactamente 1 objeto de datos con {P_TIPO_DDD} = Raíz; agrega {len(raices)}")
                continue
            raiz = raices[0]
            raiz_de[ag] = raiz
            datos = [i for i in contenido if self.c(i).tipo == "DataObject" and i != raiz]
            for i in datos:
                if self.c(i).prop(P_TIPO_DDD) not in ("Entidad", "Objeto de valor"):
                    self.error("agregado", f"{self.ref(i)} está en {self.ref(ag)} con {P_TIPO_DDD} = {self.c(i).prop(P_TIPO_DDD)!r}")
            entidades = [i for i in datos if self.c(i).prop(P_TIPO_DDD) == "Entidad"]
            vos = [i for i in datos if self.c(i).prop(P_TIPO_DDD) == "Objeto de valor"]
            # Lo que la raíz o una entidad compone también tiene que estar en el agregado.
            for dueno in [raiz] + entidades:
                for r in self.salen(dueno, "Composition", "DataObject"):
                    if r.destino not in datos:
                        self.error("composición", f"{self.ref(dueno)} compone a {self.ref(r.destino)}, que no está en {self.ref(ag)}")

            def parte(i, duenos_validos):
                comps = self.llegan(i, "Composition", "DataObject")
                validas = [r for r in comps if r.origen in duenos_validos]
                if len(comps) != 1 or len(validas) != 1:
                    self.error("composición", f"{self.ref(i)} debe tener exactamente 1 composición desde su raíz o entidad; tiene {len(comps)} ({len(validas)} desde su raíz o entidad)")
                    return None
                card = validas[0].prop("Cardinalidad")
                if card not in CARDINALIDADES:
                    self.error("composición", f"la composición {validas[0].id} hacia {self.ref(i)} tiene Cardinalidad = {card!r}; se espera {', '.join(CARDINALIDADES)}")
                return {"id": i, "nombre": self.c(i).nombre, "compuesto_por": validas[0].origen,
                        "cardinalidad": card, "composicion_id": validas[0].id, "campos": self.campos(i)}

            ents_json = [p for p in (parte(i, {raiz}) for i in self.por_nombre(entidades, g)) if p]
            vos_json = [p for p in (parte(i, {raiz, *entidades}) for i in self.por_nombre(vos, g)) if p]
            raiz_json = {"id": raiz, "nombre": self.c(raiz).nombre, "campos": self.campos(raiz)}
            for obj in [raiz_json] + ents_json + vos_json:
                for campo in obj["campos"]:
                    if campo["enum"]:
                        e = enums.setdefault(campo["enum"]["nombre"], {"nombre": campo["enum"]["nombre"],
                                                                      "valores": campo["enum"]["valores"], "usado_en": []})
                        if e["valores"] != campo["enum"]["valores"]:
                            self.error("enum", f'el enum "{e["nombre"]}" tiene valores distintos en {self.ref(obj["id"])}')
                        e["usado_en"].append({"objeto_id": obj["id"], "campo": campo["nombre"]})
            agregados_json.append({"id": ag, "nombre": self.c(ag).nombre, "raiz": raiz_json,
                                   "entidades": ents_json, "objetos_valor": vos_json})

        raices_ctx = set(raiz_de.values())

        # Comandos: acceso a su raíz, lecturas de otras raíces, eventos, contrato.
        comandos_json, eventos_por_cmd = [], {}
        codigos = {}
        for i in self.por_nombre(comandos, g):
            cmd = self.c(i)
            codigos.setdefault(self.codigo(i, P_CODIGO_SB), []).append(i)
            ag = agregado_de.get(i)
            raiz = raiz_de.get(ag)
            propio, lee_tambien = [], []
            for r in self.salen(i, "Access"):
                destino = self.c(r.destino)
                if r.destino == raiz:
                    propio.append(r)
                elif r.destino in raices_ctx and r.acceso == "lectura":
                    lee_tambien.append({"raiz_id": r.destino, "acceso_id": r.id})
                elif r.destino in raices_ctx:
                    self.error("acceso", f"{self.ref(i)} tiene acceso de {r.acceso} a {self.ref(r.destino)}, que es raíz de otro agregado; solo se permite lectura")
                else:
                    self.error("acceso", f"{self.ref(i)} accede a {self.ref(r.destino)} ({destino.prop(P_TIPO_DDD) or destino.tipo}); solo se accede a raíces del contexto")
            if raiz and len(propio) != 1:
                self.error("acceso", f"{self.ref(i)} debe tener exactamente 1 acceso a la raíz {self.ref(raiz)}; tiene {len(propio)}")
            if propio and propio[0].acceso not in ("lectura", "escritura", "lectura y escritura"):
                self.error("acceso", f"{self.ref(i)} tiene un acceso sin especificar ({propio[0].acceso}) a su raíz")
            eventos = [r.destino for r in self.salen(i, "Triggering", "ApplicationEvent")]
            eventos_por_cmd[i] = eventos
            # Sin código no hay con qué buscar su contrato: ya se informó que falta.
            sn, k = self.contrato(i, self.codigo(i, P_CODIGO_SB)) if self.codigo(i, P_CODIGO_SB) else (None, None)
            comandos_json.append({
                "id": i, "nombre": cmd.nombre, "codigo": self.codigo(i, P_CODIGO_SB),
                "agregado_id": ag, "raiz_id": raiz,
                "acceso": propio[0].acceso if propio else None, "acceso_id": propio[0].id if propio else None,
                "lee_tambien": sorted(lee_tambien, key=lambda x: x["acceso_id"]),
                "eventos": sorted(eventos), "servicio_negocio": sn, "contrato": k,
            })

        # Eventos: los de los agregados del contexto más los que disparan sus comandos.
        eventos = set()
        for ag in agregados:
            eventos |= {r.destino for r in self.salen(ag, "Aggregation", "ApplicationEvent")}
        for lista in eventos_por_cmd.values():
            eventos |= set(lista)
        eventos_json = []
        for e in self.por_nombre(eventos, g):
            ags = [r.origen for r in self.llegan(e, "Aggregation", "Grouping") if r.origen in agrupaciones_agr]
            if len(ags) != 1 or ags[0] not in agregados:
                self.error("evento", f"{self.ref(e)} debe estar en 1 agrupación \"{PREFIJO_AGREGADO}...\" del contexto; está en {len(ags)}")
            disparan = sorted(i for i, lista in eventos_por_cmd.items() if e in lista)
            if not disparan:
                self.error("evento", f"{self.ref(e)} no lo dispara ningún comando del contexto")
            elif len(disparan) > 1:
                self.aviso(f"{self.ref(e)} lo disparan {len(disparan)} comandos: " + ", ".join(self.c(i).nombre for i in disparan))
            eventos_json.append({"id": e, "nombre": self.c(e).nombre,
                                 "agregado_id": ags[0] if len(ags) == 1 else None, "disparado_por": disparan})

        # Políticas internas: evento del contexto -> dispara -> comando del contexto.
        politicas = []
        for e in eventos:
            for r in self.salen(e, "Triggering"):
                if r.destino in comandos:
                    politicas.append({"relacion_id": r.id, "evento_id": e, "comando_id": r.destino})
                else:
                    self.aviso(f"{self.ref(e)} dispara a {self.ref(r.destino)}, que no es comando del contexto: no se genera como política")
        politicas.sort(key=lambda p: p["relacion_id"])

        # Consultas: leen raíces del contexto; no escriben.
        consultas_json = []
        for i in self.por_nombre(consultas, g):
            q = self.c(i)
            codigos.setdefault(self.codigo(i, P_CODIGO_SB), []).append(i)
            lee = []
            for r in self.salen(i, "Access"):
                if r.destino in raices_ctx and r.acceso == "lectura":
                    lee.append({"raiz_id": r.destino, "acceso_id": r.id})
                else:
                    self.error("consulta", f"{self.ref(i)} tiene acceso de {r.acceso} a {self.ref(r.destino)}; una consulta solo lee raíces del contexto")
            sn, k = self.contrato(i, self.codigo(i, P_CODIGO_SB))
            consultas_json.append({"id": i, "nombre": q.nombre, "codigo": self.codigo(i, P_CODIGO_SB),
                                   "lee": sorted(lee, key=lambda x: x["acceso_id"]),
                                   "servicio_negocio": sn, "contrato": k})

        # Servicios SA: interfaz asignada al SA; contraparte = el único elemento con el que la
        # interfaz intercambia flujos (V9-DEC-02); entre el SA y la contraparte hay una relación
        # de servicio, en el sentido que diga el modelo (en SA-08 el SA le sirve a la contraparte).
        sas_json = []
        for i in self.por_nombre(sas, g):
            s = self.c(i)
            codigos.setdefault(self.codigo(i, P_CODIGO_SA), []).append(i)
            itfs = [r.origen for r in self.llegan(i, "Assignment", "ApplicationInterface")]
            flujos, con, sentido = [], None, None
            if len(itfs) != 1:
                self.error("servicio SA", f"{self.ref(i)} debe tener 1 interfaz asignada; tiene {len(itfs)}")
            else:
                itf = itfs[0]
                rel_flujo = [r for r in g.salen[itf] + g.llegan[itf] if r.tipo == "Flow"]
                otros = sorted({r.destino if r.origen == itf else r.origen for r in rel_flujo})
                if len(otros) != 1:
                    self.error("servicio SA", f"{self.ref(itf)} debe intercambiar flujos con 1 contraparte; lo hace con {len(otros)}")
                else:
                    con = self.c(otros[0])
                    flujos = [{"id": r.id, "nombre": r.nombre,
                               "direccion": "sale" if r.origen == itf else "entra",
                               "momento": r.prop("Momento")} for r in rel_flujo]
                    sirve = [r for r in g.salen[i] + g.llegan[i]
                             if r.tipo == "Serving" and {r.origen, r.destino} == {i, con.id}]
                    if len(sirve) != 1:
                        self.error("servicio SA", f"entre {self.ref(i)} y su contraparte {self.ref(con.id)} debe haber 1 relación de servicio; hay {len(sirve)}")
                    else:
                        sentido = "contraparte_a_sa" if sirve[0].origen == con.id else "sa_a_contraparte"
            sn, k = self.contrato(i, self.codigo(i, P_CODIGO_SA))
            sas_json.append({
                "id": i, "nombre": s.nombre, "codigo": self.codigo(i, P_CODIGO_SA),
                "interfaz": {"id": itfs[0], "nombre": self.c(itfs[0]).nombre} if len(itfs) == 1 else None,
                "contraparte": {"id": con.id, "nombre": con.nombre, "tipo": con.tipo,
                                "externo": con.prop("Externo") == "Sí", "sentido_servicio": sentido} if con else None,
                "flujos": sorted(flujos, key=lambda f: (f["nombre"], f["id"])),
                "servicio_negocio": sn, "contrato": k,
            })

        for codigo, ids in sorted(codigos.items(), key=lambda kv: str(kv[0])):
            if len(ids) > 1:
                self.error("código", f"el código {codigo} se repite en " + ", ".join(self.ref(i) for i in ids))

        # Nombres repetidos dentro del mismo tipo, entre los elementos del contexto.
        ids_ctx = {ctx, *agregados, *raices_ctx, *comandos, *eventos, *consultas, *sas}
        for a in agregados_json:
            ids_ctx |= {x["id"] for x in a["entidades"] + a["objetos_valor"]}
        for x in comandos_json + consultas_json + sas_json:
            ids_ctx |= {y["id"] for y in (x["servicio_negocio"], x["contrato"]) if y}
        for x in sas_json:
            ids_ctx |= {y["id"] for y in (x["interfaz"], x["contraparte"]) if y}
        vistos = {}
        for i in sorted(ids_ctx):
            vistos.setdefault((self.c(i).tipo, self.c(i).nombre), []).append(i)
        for (t, n), ids in sorted(vistos.items()):
            if len(ids) > 1:
                self.error("nombre repetido", f'{len(ids)} elementos {t} se llaman "{n}": {", ".join(ids)}')

        # Catálogo de los eventos de los otros contextos (componentes asignados a comandos con código SB),
        # para revisar en el YAML los eventos que llegan de afuera.
        otros = []
        for comp in g.elementos("ApplicationComponent"):
            if comp.id == ctx:
                continue
            cmds = [r.destino for r in self.salen(comp.id, "Assignment", "ApplicationProcess")
                    if self.codigo(r.destino, P_CODIGO_SB)]
            if cmds:
                evs = {r.destino for i in cmds for r in self.salen(i, "Triggering", "ApplicationEvent")}
                otros.append({"id": comp.id, "nombre": comp.nombre,
                              "eventos": [{"id": e, "nombre": self.c(e).nombre} for e in self.por_nombre(evs, g)]})

        return {
            "id": ctx, "nombre": nombre_ctx,
            "agregados": agregados_json,
            "comandos": comandos_json,
            "eventos": eventos_json,
            "politicas": politicas,
            "consultas": consultas_json,
            "servicios_sa": sas_json,
            "enums": sorted(enums.values(), key=lambda e: e["nombre"]),
            "otros_contextos": otros,
        }


def resumen(ctx: dict) -> list[str]:
    ags = ctx["agregados"]
    lineas = [f'Contexto "{ctx["nombre"]}" ({ctx["id"]})',
              f"  agregados: {len(ags)}"]
    for a in ags:
        lineas.append(f'    {a["nombre"]}: raíz "{a["raiz"]["nombre"]}" con {len(a["raiz"]["campos"])} campo(s) propio(s), '
                      f'{len(a["entidades"])} entidad(es), {len(a["objetos_valor"])} objeto(s) de valor')
        for v in a["entidades"] + a["objetos_valor"]:
            lineas.append(f'      - {v["nombre"]} ({v["cardinalidad"]}): ' + ", ".join(f'{c["nombre"]} {c["tipo"]}' for c in v["campos"]))
    lineas.append(f'  comandos: {len(ctx["comandos"])}')
    for c in ctx["comandos"]:
        lineas.append(f'    {c["codigo"]} {c["nombre"]}: {c["acceso"]}, {len(c["eventos"])} evento(s), '
                      f'lee también {len(c["lee_tambien"])}, contrato {"sí" if c["contrato"] else "NO"}')
    lineas.append(f'  eventos: {len(ctx["eventos"])}')
    lineas.append(f'  políticas internas: {len(ctx["politicas"])}')
    lineas.append(f'  consultas: {len(ctx["consultas"])} (' + ", ".join(f'{q["codigo"]} {q["nombre"]}' for q in ctx["consultas"]) + ")")
    lineas.append(f'  servicios SA: {len(ctx["servicios_sa"])} (' + ", ".join(s["codigo"] for s in ctx["servicios_sa"]) + ")")
    lineas.append(f'  enums: {len(ctx["enums"])} (' + ", ".join(e["nombre"] for e in ctx["enums"]) + ")")
    return lineas


def main():
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ruta_modelo, ruta_json, *nombres_ctx = sys.argv[1:]
    g = leer.leer(ruta_modelo)
    ex = Extractor(g)
    nombres_ctx = nombres_ctx or ex.contextos()
    if not nombres_ctx:
        ex.error("contexto", "el modelo no tiene contextos: ningún componente de aplicación tiene asignado un proceso "
                             f"con la propiedad {NOMBRE_SB}")
    ctxs = [ex.extraer(n) for n in nombres_ctx]
    for a in ex.avisos:
        print("AVISO:", a)
    if ex.errores:
        print(f"\nSe encontraron {len(ex.errores)} error(es); no se escribió {ruta_json}:", file=sys.stderr)
        for e in ex.errores:
            print("  ERROR", e, file=sys.stderr)
        sys.exit(1)
    salida = {
        "generado_desde": {"modelo_id": g.id, "modelo_nombre": g.nombre, "archivo": Path(ruta_modelo).name},
        "contextos": ctxs,
    }
    texto = json.dumps(salida, ensure_ascii=False, indent=2) + "\n"
    Path(ruta_json).write_bytes(texto.encode("utf-8"))      # UTF-8 sin BOM y fin de línea LF
    for ctx in ctxs:
        print("\n".join(resumen(ctx)))
    print(f"\nEscrito: {ruta_json}")


if __name__ == "__main__":
    main()
