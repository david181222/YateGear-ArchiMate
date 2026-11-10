// Generado desde ArchiMate: ApplicationComponent "Contexto Operación del arriendo" (id-909c52d6cdf845e6927af4c62d2847fb).
// Registro del contexto en el programa (host): servicios, políticas y endpoints. No editar: el generador
// reescribe este archivo. El host llama a AgregarServicios y a MapearEndpoints.
#nullable enable
using System.Text.Json;
using YateGear.Integracion;

namespace YateGear.OperacionDelArriendo;

/// <summary>Registra el contexto "Contexto Operación del arriendo" en el programa.</summary>
public static class Registro
{
    /// <summary>Nombre del contexto en la documentación de la API: agrupa sus endpoints.</summary>
    private const string Contexto = "Operación del arriendo";

    /// <summary>Servicios del contexto.</summary>
    public static void AgregarServicios(IServiceCollection servicios)
    {
        // Infraestructura (no sale del modelo): bitácora, bus de eventos y repositorio en memoria.
        // El bus del contexto publica también en el bus entre contextos, por nombre y en JSON (D1).
        servicios.AddSingleton<Bitacora>();
        servicios.AddSingleton(s => new BusDeEventos(s.GetRequiredService<Bitacora>(),
            s.GetRequiredService<BusEntreContextos>(), "Contexto Operación del arriendo"));
        servicios.AddSingleton(new Repositorio<ActaDeEntrega>());
        servicios.AddSingleton(new Repositorio<ActaDeInspeccion>());
        servicios.AddSingleton(new Repositorio<LecturaDeUbicacionYCombustible>());
        servicios.AddSingleton<MemoriaDeEventos>();

        // Servicios de la capa anticorrupción, simulados.
        servicios.AddSingleton<IEmisorDeAvisosYActasDeLasMarinas, EmisorDeAvisosYActasDeLasMarinasSimulado>();          // solo envía (G11)

        // Manejadores de comandos y consultas.
        servicios.AddSingleton<DetectarLaPerdidaDeSenalManejador>();
        servicios.AddSingleton<DeterminarLasDiferenciasEntreEntregaYDevolucionManejador>();
        servicios.AddSingleton<RegistrarElActaDeEntregaManejador>();
        servicios.AddSingleton<RegistrarLaInspeccionDeDevolucionManejador>();
        servicios.AddSingleton<RegistrarLecturasDeUbicacionYCombustibleManejador>();
        servicios.AddSingleton<ConsultarUbicacionYCombustibleDelYateManejador>();

        // Lo que reciben los servicios SA (G7): un receptor por SA.
        servicios.AddSingleton<ReceptorDeAvisosYActasDeLasMarinas>();
        servicios.AddSingleton<ReceptorDeUbicacionYCombustibleDelProveedor>();

        // Comandos que corren solos cada cierto tiempo (temporizador del YAML, G8).
        servicios.AddHostedService<DetectarLaPerdidaDeSenalTemporizador>();

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
        entreContextos.Suscribir("Contexto Gestión del arriendo", "Reserva confirmada",
            m => receptorEntreContextos.RecibirReservaConfirmada(m.DatosConIdentidad("numeroDelArriendo")));

        // Comandos: POST con el comando en JSON.
        app.MapPost("/operacion-del-arriendo/comandos/detectar-la-perdida-de-senal",
            (DetectarLaPerdidaDeSenal comando, DetectarLaPerdidaDeSenalManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-27: Detectar la pérdida de señal",
                "Entrada: Arriendo en curso y tiempo máximo sin lecturas.\n\nSalida: Alerta de pérdida de señal con la última lectura conocida.\n\nReglas: El tiempo sin lecturas que dispara la alerta lo fija Operaciones (V4-SUP-04). Contactar al cliente lo hace la marina; el software solo detecta y avisa (EXC-01).", 404, 409, 422);
        app.MapPost("/operacion-del-arriendo/comandos/determinar-las-diferencias-entre-entrega-y-devolucion",
            (DeterminarLasDiferenciasEntreEntregaYDevolucion comando, DeterminarLasDiferenciasEntreEntregaYDevolucionManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-24: Determinar las diferencias entre entrega y devolución",
                "Entrada: Arriendo y fecha y hora de fin acordadas.\n\nSalida: Combustible consumido, horas adicionales y daños, con la evidencia de cada uno.\n\nReglas: Se rechaza si falta el acta de entrega o la de inspección, porque la comparación de las dos es la evidencia (H-13).", 404, 409, 422);
        app.MapPost("/operacion-del-arriendo/comandos/registrar-el-acta-de-entrega",
            (RegistrarElActaDeEntrega comando, RegistrarElActaDeEntregaManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-22: Registrar el acta de entrega",
                "Entrada: Arriendo, identificador del yate, fotos, nivel de combustible, hora de entrega y observaciones.\n\nSalida: Acta de entrega registrada.\n\nReglas: Se rechaza si el arriendo no tiene la reserva confirmada (CIE-01) o si el acta no trae fotos (H-13).", 404, 409, 422);
        app.MapPost("/operacion-del-arriendo/comandos/registrar-la-inspeccion-de-devolucion",
            (RegistrarLaInspeccionDeDevolucion comando, RegistrarLaInspeccionDeDevolucionManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-23: Registrar la inspección de devolución",
                "Entrada: Arriendo, fotos, nivel de combustible, hora de regreso y daños encontrados con su valor.\n\nSalida: Acta de inspección registrada.\n\nReglas: Se rechaza una inspección sin fotos (H-13). El valor de los daños llega con la inspección (V4-SUP-03).", 404, 409, 422);
        app.MapPost("/operacion-del-arriendo/comandos/registrar-lecturas-de-ubicacion-y-combustible",
            (RegistrarLecturasDeUbicacionYCombustible comando, RegistrarLecturasDeUbicacionYCombustibleManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-25: Registrar lecturas de ubicación y combustible",
                "Entrada: Yate, posición, nivel de combustible y hora de la lectura.\n\nSalida: Lectura guardada.", 404, 409, 422);

        // Consultas: GET con la identidad en la ruta.
        app.MapGet("/operacion-del-arriendo/consultas/consultar-ubicacion-y-combustible-del-yate",
            (string numeroDelArriendo, ConsultarUbicacionYCombustibleDelYateManejador manejador) => Ejecutar(() => manejador.Manejar(new ConsultarUbicacionYCombustibleDelYate(numeroDelArriendo))))
            .Documentar<ConsultarUbicacionYCombustibleDelYateSalida>("Consulta SB-26: Consultar ubicación y combustible del yate",
                "Entrada: Arriendo en curso y quién consulta.\n\nSalida: Última posición, nivel de combustible, hora y recorrido.\n\nReglas: Se rechaza si quien consulta no es el cliente del arriendo ni la marina que guarda el yate (V4-SUP-05).", 404, 422);

        // Eventos de otros contextos (capa 3): POST con el evento en JSON. Si falta un dato obligatorio
        // responde 422; si faltan eventos de su grupo (junto_con), 202.
        app.MapPost("/operacion-del-arriendo/eventos-externos/reserva-confirmada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirReservaConfirmada(evento), Recibido))
            .Accepts<ReservaConfirmada>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Reserva confirmada\" de Contexto Gestión del arriendo",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);


        // Lo que reciben los servicios SA (G7): POST con el mensaje en JSON. Si falta un dato obligatorio responde 422.
        app.MapPost("/operacion-del-arriendo/sa/avisos-y-actas-de-las-marinas/acta-de-entrega-recibida",
            (JsonElement mensaje, ReceptorDeAvisosYActasDeLasMarinas receptor) => Ejecutar(() => receptor.RecibirActaDeEntregaRecibida(mensaje)))
            .Accepts<ActaDeEntregaRecibida>("application/json")
            .Documentar<RespuestaDeComando>("Mensaje \"Acta de entrega recibida\" que recibe SA-05 Avisos y actas de las marinas",
                "Lo que el sistema externo le envía a la aplicación. Dispara: Registrar el acta de entrega.", 404, 409, 422);
        app.MapPost("/operacion-del-arriendo/sa/avisos-y-actas-de-las-marinas/acta-de-inspeccion-recibida",
            (JsonElement mensaje, ReceptorDeAvisosYActasDeLasMarinas receptor) => Ejecutar(() => receptor.RecibirActaDeInspeccionRecibida(mensaje)))
            .Accepts<ActaDeInspeccionRecibida>("application/json")
            .Documentar<RespuestaDeComando>("Mensaje \"Acta de inspección recibida\" que recibe SA-05 Avisos y actas de las marinas",
                "Lo que el sistema externo le envía a la aplicación. Dispara: Registrar la inspección de devolución.", 404, 409, 422);
        app.MapPost("/operacion-del-arriendo/sa/ubicacion-y-combustible-del-proveedor/lectura-del-proveedor",
            (JsonElement mensaje, ReceptorDeUbicacionYCombustibleDelProveedor receptor) => Ejecutar(() => receptor.RecibirLecturaDelProveedor(mensaje)))
            .Accepts<LecturaDelProveedor>("application/json")
            .Documentar<RespuestaDeComando>("Mensaje \"Lectura del proveedor\" que recibe SA-07 Ubicación y combustible del proveedor",
                "Lo que el sistema externo le envía a la aplicación. Dispara: Registrar lecturas de ubicación y combustible.", 404, 409, 422);

        // Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
        app.MapGet("/operacion-del-arriendo/bitacora", (Bitacora bitacora) => bitacora.Todo())
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
