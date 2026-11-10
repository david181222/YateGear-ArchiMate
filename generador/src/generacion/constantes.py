"""Constantes de la generación: carpetas, nombres fijos y nombres reservados de C#."""
from __future__ import annotations

from pathlib import Path

DIR_PLANTILLAS = Path(__file__).resolve().parent.parent.parent / "plantillas"
# Versión de .NET de lo generado: el destino de los proyectos y el SDK mínimo de global.json (rollForward: latestFeature).
NET = "net10.0"
SDK = "10.0.100"
# Paquetes NuGet del host para la documentación de la API, con versión fija: el documento OpenAPI y la página Swagger.
PAQUETES_DEL_HOST = (("Microsoft.AspNetCore.OpenApi", "10.0.15"), ("Swashbuckle.AspNetCore.SwaggerUI", "10.3.1"))
TIPO_PROYECTO_CS = "9A19103F-16F7-4668-BE54-9A1E7A4F7556"     # tipo de proyecto "C# SDK" en una solución
CARPETAS_MANUALES = ("Comandos", "Consultas")
PUERTO_POR_DEFECTO = 5080           # puerto de la aplicación, si no se da otro (generar.py --puerto)
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
