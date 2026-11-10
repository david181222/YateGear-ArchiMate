"""Revisor del YAML de un contexto. Cada sección del YAML se revisa en su módulo."""
from __future__ import annotations

from pathlib import Path

from comun import tipos
from validacion.revisor_comandos import RevisionDeComandos
from validacion.revisor_consultas import RevisionDeConsultas
from validacion.revisor_escenarios import RevisionDeEscenarios
from validacion.revisor_eventos import RevisionDeEventos
from validacion.revisor_raices import RevisionDeRaices
from validacion.revisor_servicios_sa import RevisionDeServiciosSA
from validacion.valores import mismo_tipo, valor_valido


class Revisor(RevisionDeRaices, RevisionDeServiciosSA, RevisionDeComandos, RevisionDeEventos, RevisionDeConsultas,
              RevisionDeEscenarios):
    """Revisa el YAML de un contexto contra el modelo. Junta los errores en errores y los avisos en avisos."""

    def __init__(self, modelo: dict, spec, nombre_archivo: str):
        self.m = modelo
        self.s = spec
        self.archivo = nombre_archivo
        self.errores: list[str] = []
        self.avisos: list[str] = []
        self.enums: dict[str, list[str]] = {}
        self.varios_origenes: list[str] = []   # datos que llegan de más de un origen (informativo)
        self.id_nombre = ""                    # la identidad de la raíz actual (ver usar)

    # ------------------------------------------------------------ utilidades
    def error(self, donde: str, texto: str):
        self.errores.append(f"[{donde}] {texto}")

    def aviso(self, donde: str, texto: str):
        self.avisos.append(f"[{donde}] {texto}")

    def mapa(self, x, donde: str, permitidas=None, obligatorias=()) -> dict:
        if x is None:
            x = {}
        if not isinstance(x, dict):
            self.error(donde, f"se esperaba una sección con claves y se encontró {type(x).__name__}")
            return {}
        if permitidas is not None:
            for k in x:
                if k not in permitidas:
                    self.error(donde, f'clave desconocida "{k}"; se permiten: {", ".join(permitidas)}')
        for k in obligatorias:
            if k not in x:
                self.error(donde, f'falta la clave "{k}"')
        return x

    def lista(self, x, donde: str) -> list:
        if x is None:
            return []
        if not isinstance(x, list):
            self.error(donde, f"se esperaba una lista y se encontró {type(x).__name__}")
            return []
        return x

    def tipo(self, texto, donde: str) -> dict | None:
        try:
            t = tipos.interpretar(texto)
        except tipos.TipoInvalido as e:
            self.error(donde, str(e))
            return None
        if t["enum"]:
            n, v = t["enum"]["nombre"], t["enum"]["valores"]
            if self.enums.setdefault(n, v) != v:
                self.error(donde, f'el enum "{n}" ya existe con otros valores: {", ".join(self.enums[n])}')
        return t

    def campos(self, x, donde: str, libres: bool = False, permitidos=()) -> dict[str, dict]:
        """Datos "nombre: tipo". La identidad y el estado se agregan solos, así que solo se
        pueden escribir donde se piden o se devuelven (libres=True): entrada de un SA y salida de una consulta."""
        out = {}
        for nombre, texto in self.mapa(x, donde).items():
            if not isinstance(nombre, str) or not nombre.strip():
                self.error(donde, f"nombre de dato vacío o inválido: {nombre!r}")
                continue
            if not libres and nombre in (self.id_nombre, "estado") and nombre not in permitidos:
                self.error(donde, f'"{nombre}" se agrega solo; no se escribe en el YAML')
                continue
            t = self.tipo(texto, f'{donde} > {nombre}')
            if t:
                out[nombre] = t
        return out

    def cubre(self, seccion: str, del_yaml: dict, del_modelo: dict, tipo: str):
        for n in sorted(set(del_modelo) - set(del_yaml)):
            self.error(seccion, f'falta en el YAML: {tipo} "{n}" ({del_modelo[n]["id"]})')
        for n in sorted(set(del_yaml) - set(del_modelo)):
            self.error(seccion, f'"{n}" no existe en el modelo como {tipo} del contexto')

    def agregar(self, bolsa: dict, nuevos: dict, donde: str):
        for n, t in nuevos.items():
            if n in bolsa and not mismo_tipo(bolsa[n], t):
                self.error(donde, f'el dato "{n}" ya existe como {bolsa[n]["tipo"]} y aquí llega como {t["tipo"]}')
            else:
                bolsa[n] = t

    def pide(self, bolsa: dict, necesarios: dict, donde: str, quien: str, propios=frozenset()):
        """Revisa que cada dato necesario esté en la bolsa, con su tipo y con un solo origen.

        propios: nombres que llegan por la entrada o por un SA; esos no dependen de la raíz.
        """
        for n, t in necesarios.items():
            if n in self.ambiguos and n not in propios:
                self.error(donde, f'{quien} usa "{n}", que puede venir de {" y de ".join(self.ambiguos[n])}')
            elif n not in bolsa:
                self.error(donde, f'{quien} necesita "{n}" ({t["tipo"]}) y no está disponible por ese nombre')
            elif not mismo_tipo(bolsa[n], t):
                self.error(donde, f'{quien} necesita "{n}" como {t["tipo"]} y está disponible como {bolsa[n]["tipo"]}')

    def estados_validos(self, valores, donde: str) -> list[str]:
        out = []
        for e in self.lista(valores, donde) if isinstance(valores, list) else [valores]:
            if e not in self.estados:
                self.error(donde, f'"{e}" no es un estado de la raíz; estados: {", ".join(self.estados)}')
            else:
                out.append(e)
        return out

    def condicion(self, si, bolsa: dict, donde: str, propios=frozenset()) -> dict[str, set]:
        out = {}
        for campo, valores in self.mapa(si, donde).items():
            if campo in self.ambiguos and campo not in propios:
                self.error(donde, f'la condición usa "{campo}", que puede venir de {" y de ".join(self.ambiguos[campo])}')
                continue
            if campo not in bolsa:
                self.error(donde, f'la condición usa "{campo}", que no está disponible')
                continue
            t = bolsa[campo]
            if t["lista"]:
                self.error(donde, f'la condición no puede usar la lista "{campo}"')
                continue
            vals = self.lista(valores, f"{donde} > {campo}")
            for v in vals:
                if not valor_valido(v, {**t, "opcional": False}):
                    self.error(donde, f'el valor {v!r} no es válido para "{campo}" ({t["tipo"]})')
            out[campo] = set(map(str, vals))
        return out

    def si_salvo(self, x: dict, bolsa: dict, donde: str, propios=frozenset()):
        """Condiciones si (el dato está entre esos valores) y salvo (no está entre ellos) sobre los datos disponibles."""
        for k in ("si", "salvo"):
            if k in x:
                self.condicion(x[k], bolsa, f"{donde} > {k}", propios)

    def revisar_valores(self, valores, bolsa: dict, donde: str, todos: dict) -> list[str]:
        """Valores fijos: solo para datos de la raíz o de sus objetos de valor, cuyo tipo sale del modelo.
        Los agrega a la bolsa y devuelve sus nombres."""
        out = []
        for k, v in self.mapa(valores, donde).items():
            t_v = (todos.get(k) or self.componentes.get(k)) if k not in (self.id_nombre, "estado") else None
            if t_v is None:
                self.error(donde, f'"{k}" no es un campo de la raíz ni de sus objetos de valor')
            elif not valor_valido(v, t_v):
                self.error(donde, f'el valor {v!r} no es válido para "{k}" ({t_v["tipo"]})')
            else:
                self.agregar(bolsa, {k: t_v}, donde)
                out.append(k)
        return out

    # ------------------------------------------------------------ revisión
    def revisar(self):
        """Revisa el YAML sección por sección. Los errores quedan en errores; no se detiene en el primero."""
        if not self.revisar_raices():
            return
        self.revisar_servicios_sa()
        self.revisar_comandos()
        self.revisar_mensajes_sa()
        self.revisar_eventos()
        self.revisar_politicas()
        self.revisar_envios_sa()
        self.revisar_consultas()
        self.revisar_eventos_externos()
        self.revisar_escenarios()

    def revisar_raices(self) -> bool:
        """Las claves del archivo, el contexto y sus raíces. Devuelve False si no se puede seguir revisando."""
        s = self.mapa(self.s, "archivo", ["contexto", "raices", "comandos", "eventos", "consultas",
                                          "eventos_de_otros_contextos", "servicios_sa", "politicas", "escenarios"],
                      ["contexto", "raices", "comandos", "eventos", "consultas", "servicios_sa"])
        ctxs = {c["nombre"]: c for c in self.m["contextos"]}
        if s.get("contexto") not in ctxs:
            self.error("contexto", f'"{s.get("contexto")}" no está en el JSON; contextos: {", ".join(ctxs)}')
            return False
        ctx = self.ctx = ctxs[s["contexto"]]
        for e in ctx["enums"]:
            self.enums[e["nombre"]] = e["valores"]
        # Los objetos de valor y las entidades del contexto se pueden usar como List<...> en el YAML.
        tipos.usar_objetos({v["nombre"]: {c["nombre"]: c for c in v["campos"]}
                            for a in ctx["agregados"] for v in a["objetos_valor"] + a["entidades"]})
        agregados = {a["raiz"]["id"]: a for a in ctx["agregados"]}
        raices_m = {a["raiz"]["nombre"]: {"id": a["raiz"]["id"]} for a in ctx["agregados"]}
        raices_y = self.mapa(s.get("raices"), "raices")
        self.cubre("raices", raices_y, raices_m, "raíz")
        if not raices_m:
            self.error("raices", "el contexto no tiene agregados")
            return False
        # Cada raíz se prepara por separado; cada comando, evento, consulta y paso usa la de su agregado.
        self.raices = {n: self.preparar_raiz(n, agregados[raices_m[n]["id"]], raices_y.get(n)) for n in sorted(raices_m)}
        self.raiz_por_id = {rc["id"]: rc for rc in self.raices.values()}
        self.raiz_por_agregado = {rc["agregado_id"]: rc for rc in self.raices.values()}
        self.usar(next(iter(self.raices.values())))
        return True

    def resumen(self) -> list[str]:
        s = self.s
        texto = Path(self.archivo).read_text(encoding="utf-8")
        n_sup = sum(1 for linea in texto.splitlines() if "# supuesto" in linea and '"# supuesto"' not in linea)
        return [f'{s["contexto"]}: {len(s["raices"])} raíz, {len(s["comandos"])} comandos, {len(s["eventos"])} eventos, '
                f'{len(s["consultas"])} consultas, {len(s.get("eventos_de_otros_contextos") or {})} eventos de otros '
                f'contextos, {len(s["servicios_sa"])} servicios SA, {len(s.get("escenarios") or {})} escenarios; {len(self.enums)} enums; '
                f'{n_sup} líneas con "# supuesto".']
