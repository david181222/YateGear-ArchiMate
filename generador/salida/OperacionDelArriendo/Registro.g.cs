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

        // Comandos: POST con el comando en JSON.
        app.MapPost("/operacion-del-arriendo/comandos/detectar-la-perdida-de-senal",
            (DetectarLaPerdidaDeSenal comando, DetectarLaPerdidaDeSenalManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/operacion-del-arriendo/comandos/determinar-las-diferencias-entre-entrega-y-devolucion",
            (DeterminarLasDiferenciasEntreEntregaYDevolucion comando, DeterminarLasDiferenciasEntreEntregaYDevolucionManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/operacion-del-arriendo/comandos/registrar-el-acta-de-entrega",
            (RegistrarElActaDeEntrega comando, RegistrarElActaDeEntregaManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/operacion-del-arriendo/comandos/registrar-la-inspeccion-de-devolucion",
            (RegistrarLaInspeccionDeDevolucion comando, RegistrarLaInspeccionDeDevolucionManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/operacion-del-arriendo/comandos/registrar-lecturas-de-ubicacion-y-combustible",
            (RegistrarLecturasDeUbicacionYCombustible comando, RegistrarLecturasDeUbicacionYCombustibleManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));

        // Consultas: GET con la identidad en la ruta.
        app.MapGet("/operacion-del-arriendo/consultas/consultar-ubicacion-y-combustible-del-yate",
            (string numeroDelArriendo, ConsultarUbicacionYCombustibleDelYateManejador manejador) => Ejecutar(() => manejador.Manejar(new ConsultarUbicacionYCombustibleDelYate(numeroDelArriendo))));

        // Eventos de otros contextos (capa 3): POST con el evento en JSON. Si falta un dato obligatorio
        // responde 422; si faltan eventos de su grupo (junto_con), 202.
        app.MapPost("/operacion-del-arriendo/eventos-externos/reserva-confirmada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirReservaConfirmada(evento), Recibido));


        // Lo que reciben los servicios SA (G7): POST con el mensaje en JSON. Si falta un dato obligatorio responde 422.
        app.MapPost("/operacion-del-arriendo/sa/avisos-y-actas-de-las-marinas/acta-de-entrega-recibida",
            (JsonElement mensaje, ReceptorDeAvisosYActasDeLasMarinas receptor) => Ejecutar(() => receptor.RecibirActaDeEntregaRecibida(mensaje)));
        app.MapPost("/operacion-del-arriendo/sa/avisos-y-actas-de-las-marinas/acta-de-inspeccion-recibida",
            (JsonElement mensaje, ReceptorDeAvisosYActasDeLasMarinas receptor) => Ejecutar(() => receptor.RecibirActaDeInspeccionRecibida(mensaje)));
        app.MapPost("/operacion-del-arriendo/sa/ubicacion-y-combustible-del-proveedor/lectura-del-proveedor",
            (JsonElement mensaje, ReceptorDeUbicacionYCombustibleDelProveedor receptor) => Ejecutar(() => receptor.RecibirLecturaDelProveedor(mensaje)));

        // Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
        app.MapGet("/operacion-del-arriendo/bitacora", (Bitacora bitacora) => bitacora.Todo());
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
