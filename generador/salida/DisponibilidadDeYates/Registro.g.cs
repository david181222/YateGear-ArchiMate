// Generado desde ArchiMate: ApplicationComponent "Contexto Disponibilidad de yates" (id-0d93d731f6fd4b21acbf20d3cb28cf6f).
// Registro del contexto en el programa (host): servicios, políticas y endpoints. No editar: el generador
// reescribe este archivo. El host llama a AgregarServicios y a MapearEndpoints.
#nullable enable
using System.Text.Json;
using YateGear.Integracion;

namespace YateGear.DisponibilidadDeYates;

/// <summary>Registra el contexto "Contexto Disponibilidad de yates" en el programa.</summary>
public static class Registro
{
    /// <summary>Servicios del contexto.</summary>
    public static void AgregarServicios(IServiceCollection servicios)
    {
        // Infraestructura (no sale del modelo): bitácora, bus de eventos y repositorio en memoria.
        // El bus del contexto publica también en el bus entre contextos, por nombre y en JSON (D1).
        servicios.AddSingleton<Bitacora>();
        servicios.AddSingleton(s => new BusDeEventos(s.GetRequiredService<Bitacora>(),
            s.GetRequiredService<BusEntreContextos>(), "Contexto Disponibilidad de yates"));
        servicios.AddSingleton(new Repositorio<CalendarioDelYate>());
        servicios.AddSingleton(new Repositorio<Yate>("YATE-", 4));

        // Servicios de la capa anticorrupción, simulados.
        servicios.AddSingleton<IContratosConPropietariosYClientes, ContratosConPropietariosYClientesSimulado>();

        // Manejadores de comandos y consultas.
        servicios.AddSingleton<DefinirLasFechasBloqueadasDelYateManejador>();
        servicios.AddSingleton<GestionarLaOcupacionDelCalendarioManejador>();
        servicios.AddSingleton<RegistrarYateEnElInventarioManejador>();
        servicios.AddSingleton<ConsultarYatesDisponiblesManejador>();

        // Eventos de otros contextos (capa 3): receptor y espera de los que deben llegar juntos.
        servicios.AddSingleton<EsperaDeEventos>();
        servicios.AddSingleton<ReceptorDeEventosExternos>();
    }

    /// <summary>Políticas y endpoints del contexto.</summary>
    public static void MapearEndpoints(WebApplication app)
    {
        Politicas.Registrar(app.Services);

        // Comandos: POST con el comando en JSON.
        app.MapPost("/disponibilidad-de-yates/comandos/definir-las-fechas-bloqueadas-del-yate",
            (DefinirLasFechasBloqueadasDelYate comando, DefinirLasFechasBloqueadasDelYateManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/disponibilidad-de-yates/comandos/gestionar-la-ocupacion-del-calendario",
            (GestionarLaOcupacionDelCalendario comando, GestionarLaOcupacionDelCalendarioManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/disponibilidad-de-yates/comandos/registrar-yate-en-el-inventario",
            (RegistrarYateEnElInventario comando, RegistrarYateEnElInventarioManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));

        // Consultas: GET con la identidad en la ruta.
        app.MapGet("/disponibilidad-de-yates/consultas/consultar-yates-disponibles",
            (string identificadorDeLaMarina, DateOnly inicio, DateOnly fin, ConsultarYatesDisponiblesManejador manejador) => Ejecutar(() => manejador.Manejar(new ConsultarYatesDisponibles(identificadorDeLaMarina, inicio, fin))));

        // Eventos de otros contextos (capa 3): POST con el evento en JSON. Si falta un dato obligatorio
        // responde 422; si faltan eventos de su grupo (junto_con), 202.
        app.MapPost("/disponibilidad-de-yates/eventos-externos/arriendo-no-realizado-por-riesgo-alto",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirArriendoNoRealizadoPorRiesgoAlto(evento), Recibido));
        app.MapPost("/disponibilidad-de-yates/eventos-externos/reserva-cancelada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirReservaCancelada(evento), Recibido));
        app.MapPost("/disponibilidad-de-yates/eventos-externos/reserva-confirmada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirReservaConfirmada(evento), Recibido));
        app.MapPost("/disponibilidad-de-yates/eventos-externos/reserva-solicitada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirReservaSolicitada(evento), Recibido));

        // Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
        app.MapGet("/disponibilidad-de-yates/bitacora", (Bitacora bitacora) => bitacora.Todo());
    }

    private static IResult Ejecutar<T>(Func<T> accion, Func<T, IResult>? exito = null)
    {
        try
        {
            var resultado = accion();
            return exito is null ? Results.Ok(resultado) : exito(resultado);
        }
        catch (NoEncontrado e)
        {
            return Results.NotFound(new { error = e.Message });
        }
        catch (TransicionInvalida e)
        {
            return Results.Conflict(new { operacion = e.Operacion, estadoActual = e.EstadoActual, permitidos = e.Permitidos });
        }
        catch (ReglaIncumplida e)
        {
            return Results.UnprocessableEntity(new { regla = e.Regla, motivo = e.Motivo });
        }
        catch (IdentidadRepetida e)
        {
            return Results.Conflict(new { identidad = e.Identidad, motivo = e.Message });
        }
        catch (FaltaEventoRequerido e)
        {
            return Results.Conflict(new { operacion = e.Operacion, requiere = e.Evento, identidad = e.Identidad });
        }
        catch (DatoFaltante e)
        {
            return Results.UnprocessableEntity(new { regla = "dato faltante", motivo = e.Message });
        }
        catch (JsonException e)
        {
            return Results.BadRequest(new { error = e.Message });
        }
    }

    private static IResult Recibido(RespuestaDeEventoExterno respuesta) =>
        respuesta.Estado == "esperando" ? Results.Accepted(null, respuesta) : Results.Ok(respuesta);
}
