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
    /// <summary>Nombre del contexto en la documentación de la API: agrupa sus endpoints.</summary>
    private const string Contexto = "Disponibilidad de yates";

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

        // Eventos de otros contextos que llegan por el bus entre contextos (G12, D1): cada uno va a su receptor, por el
        // nombre del contexto que lo publica y su nombre en el modelo. Si el receptor falla, el error queda en el bus.
        var entreContextos = app.Services.GetRequiredService<BusEntreContextos>();
        var receptorEntreContextos = app.Services.GetRequiredService<ReceptorDeEventosExternos>();
        entreContextos.Suscribir("Contexto Gestión del arriendo", "Arriendo no realizado por riesgo alto",
            m => receptorEntreContextos.RecibirArriendoNoRealizadoPorRiesgoAlto(m.DatosConIdentidad("numeroDelArriendo")));
        entreContextos.Suscribir("Contexto Gestión del arriendo", "Reserva cancelada",
            m => receptorEntreContextos.RecibirReservaCancelada(m.DatosConIdentidad("numeroDelArriendo")));
        entreContextos.Suscribir("Contexto Gestión del arriendo", "Reserva confirmada",
            m => receptorEntreContextos.RecibirReservaConfirmada(m.DatosConIdentidad("numeroDelArriendo")));
        entreContextos.Suscribir("Contexto Gestión del arriendo", "Reserva solicitada",
            m => receptorEntreContextos.RecibirReservaSolicitada(m.DatosConIdentidad("numeroDelArriendo")));

        // Comandos: POST con el comando en JSON.
        app.MapPost("/disponibilidad-de-yates/comandos/definir-las-fechas-bloqueadas-del-yate",
            (DefinirLasFechasBloqueadasDelYate comando, DefinirLasFechasBloqueadasDelYateManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-03: Definir las fechas bloqueadas del yate",
                "Entrada: Yate, fecha de inicio, fecha de fin y acción (bloquear o desbloquear).\n\nSalida: Calendario del yate actualizado.\n\nReglas: Se rechaza si quien hace el cambio no es el propietario del yate (E2E-02). Se rechaza el bloqueo de fechas que ya tienen una reserva confirmada (REG-02).", 404, 409, 422);
        app.MapPost("/disponibilidad-de-yates/comandos/gestionar-la-ocupacion-del-calendario",
            (GestionarLaOcupacionDelCalendario comando, GestionarLaOcupacionDelCalendarioManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-05: Gestionar la ocupación del calendario",
                "Entrada: Yate, fechas, arriendo y acción: apartar, ocupar o soltar.\n\nSalida: Calendario con las fechas apartadas, ocupadas o libres.\n\nReglas: Se rechaza apartar u ocupar fechas que ya tiene otro arriendo o que bloqueó el propietario: un yate no puede tener dos arriendos en las mismas fechas (REG-01). Las fechas se apartan al pedir la reserva y se ocupan al confirmarla (V4-SUP-01).", 404, 409, 422);
        app.MapPost("/disponibilidad-de-yates/comandos/registrar-yate-en-el-inventario",
            (RegistrarYateEnElInventario comando, RegistrarYateEnElInventarioManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-01: Registrar yate en el inventario",
                "Entrada: Propietario, marina, datos del yate (nombre, matrícula y capacidad), precio por día, documentos ante la DIMAR al día y contrato firmado con el propietario.\n\nSalida: Yate registrado con su identificador.\n\nReglas: Se rechaza si el propietario no tiene contrato firmado (INT-CON) o si los documentos del yate ante la DIMAR no están al día (NOR-01).", 404, 409, 422);

        // Consultas: GET con la identidad en la ruta.
        app.MapGet("/disponibilidad-de-yates/consultas/consultar-yates-disponibles",
            (string identificadorDeLaMarina, DateOnly inicio, DateOnly fin, ConsultarYatesDisponiblesManejador manejador) => Ejecutar(() => manejador.Manejar(new ConsultarYatesDisponibles(identificadorDeLaMarina, inicio, fin))))
            .Documentar<ConsultarYatesDisponiblesSalida>("Consulta SB-04: Consultar yates disponibles",
                "Entrada: Ubicación del cliente o marina elegida, fecha de inicio y fecha de fin.\n\nSalida: Lista de yates disponibles con su marina y su precio por día. Puede venir vacía.\n\nReglas: No se muestra un yate con esas fechas bloqueadas por el propietario o con otra reserva: disponible es sin bloqueo y sin otra reserva en esas fechas (H-08).", 404, 422);

        // Eventos de otros contextos (capa 3): POST con el evento en JSON. Si falta un dato obligatorio
        // responde 422; si faltan eventos de su grupo (junto_con), 202.
        app.MapPost("/disponibilidad-de-yates/eventos-externos/arriendo-no-realizado-por-riesgo-alto",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirArriendoNoRealizadoPorRiesgoAlto(evento), Recibido))
            .Accepts<ArriendoNoRealizadoPorRiesgoAlto>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Arriendo no realizado por riesgo alto\" de Contexto Gestión del arriendo",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);
        app.MapPost("/disponibilidad-de-yates/eventos-externos/reserva-cancelada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirReservaCancelada(evento), Recibido))
            .Accepts<ReservaCancelada>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Reserva cancelada\" de Contexto Gestión del arriendo",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);
        app.MapPost("/disponibilidad-de-yates/eventos-externos/reserva-confirmada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirReservaConfirmada(evento), Recibido))
            .Accepts<ReservaConfirmada>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Reserva confirmada\" de Contexto Gestión del arriendo",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);
        app.MapPost("/disponibilidad-de-yates/eventos-externos/reserva-solicitada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirReservaSolicitada(evento), Recibido))
            .Accepts<ReservaSolicitada>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Reserva solicitada\" de Contexto Gestión del arriendo",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);


        // Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
        app.MapGet("/disponibilidad-de-yates/bitacora", (Bitacora bitacora) => bitacora.Todo())
            .Documentar<IReadOnlyList<RegistroDeBitacora>>("Bitácora (infraestructura)",
                "Eventos publicados y recibidos, llamadas a los servicios SA simulados y errores, en orden. No sale del modelo.");
    }

    /// <summary>Documenta un endpoint para OpenAPI (Swagger): su contexto, de qué elemento del modelo sale, su contrato,
    /// lo que responde y los códigos con que puede rechazar.</summary>
    private static RouteHandlerBuilder Documentar<TRespuesta>(this RouteHandlerBuilder endpoint, string resumen,
        string descripcion, params int[] rechazos)
    {
        endpoint.WithTags(Contexto).WithSummary(resumen).WithDescription(descripcion).Produces<TRespuesta>();
        foreach (var codigo in rechazos)
        {
            endpoint.Produces(codigo);
        }
        return endpoint;
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
