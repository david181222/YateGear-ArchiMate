"""Constantes de la generación: carpetas, nombres fijos y nombres reservados de C#."""
from __future__ import annotations

from pathlib import Path

DIR_PLANTILLAS = Path(__file__).resolve().parent.parent.parent / "plantillas"
TIPO_PROYECTO_CS = "9A19103F-16F7-4668-BE54-9A1E7A4F7556"     # tipo de proyecto "C# SDK" en una solución
CARPETAS_MANUALES = ("Comandos", "Consultas")
PUERTO = 5080                       # puerto de la aplicación: launchSettings.json y pruebas.http
INTEGRACION = "Integracion"         # proyecto con el bus entre contextos (D1)
ARCHIVOS_GENERADOS = "intermedio/archivos-generados.txt"   # para borrar los que ya no corresponden
PRUEBAS_ENTRE_CONTEXTOS = "pruebas/EntreContextos"        # escenarios de punta a punta entre contextos (S4)
INFRAESTRUCTURA = ("IRaiz", "IEvento", "IEntidad", "Entidades", "Repositorio", "Bitacora", "RegistroDeBitacora", "BusDeEventos",
                   "RespuestaDeComando", "ReglaIncumplida", "NoEncontrado", "DatoFaltante", "Politicas", "Program",
                   "TransicionInvalida", "Estados", "EsperaDeEventos", "RespuestaDeEventoExterno",
                   "ReceptorDeEventosExternos", "Registro", "LectorDeEventos", "IdentidadRepetida",
                   "FaltaEventoRequerido", "MemoriaDeEventos",
                   "Json", "BusEntreContextos", "EventoEntreContextos")     # del bus entre contextos, que todo contexto importa
MIEMBROS_RESERVADOS = {"Manejar", "ValidarReglas", "Publicar", "Llamar"}
