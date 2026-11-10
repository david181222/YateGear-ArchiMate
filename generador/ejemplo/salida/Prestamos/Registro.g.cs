// Generado desde ArchiMate: ApplicationComponent "Contexto Préstamos" (id-ccd77ee8d6e85373b2058f86905a7b2c).
// Registro del contexto en el programa (host): servicios, políticas y endpoints. No editar: el generador
// reescribe este archivo. El host llama a AgregarServicios y a MapearEndpoints.
#nullable enable
using System.Text.Json;
using Biblioteca.Integracion;

namespace Biblioteca.Prestamos;

/// <summary>Registra el contexto "Contexto Préstamos" en el programa.</summary>
public static class Registro
{
    /// <summary>Nombre del contexto en la documentación de la API: agrupa sus endpoints.</summary>
    private const string Contexto = "Préstamos";

    /// <summary>Servicios del contexto.</summary>
    public static void AgregarServicios(IServiceCollection servicios)
    {
        // Infraestructura (no sale del modelo): bitácora, bus de eventos y repositorio en memoria.
        // El bus del contexto publica también en el bus entre contextos, por nombre y en JSON (D1).
        servicios.AddSingleton<Bitacora>();
        servicios.AddSingleton(s => new BusDeEventos(s.GetRequiredService<Bitacora>(),
            s.GetRequiredService<BusEntreContextos>(), "Contexto Préstamos"));
        servicios.AddSingleton(new Repositorio<Prestamo>("PRE-", 4));

        // Servicios de la capa anticorrupción, simulados.
        servicios.AddSingleton<ICatalogoDeLaBiblioteca, CatalogoDeLaBibliotecaSimulado>();

        // Manejadores de comandos y consultas.
        servicios.AddSingleton<DevolverElLibroManejador>();
        servicios.AddSingleton<PrestarUnLibroManejador>();
        servicios.AddSingleton<ConsultarElPrestamoManejador>();
    }

    /// <summary>Políticas y endpoints del contexto.</summary>
    public static void MapearEndpoints(WebApplication app)
    {
        Politicas.Registrar(app.Services);

        // Comandos: POST con el comando en JSON.
        app.MapPost("/prestamos/comandos/devolver-el-libro",
            (DevolverElLibro comando, DevolverElLibroManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-02: Devolver el libro",
                "Entrada: Número del préstamo.\n\nSalida: Préstamo devuelto.\n\nReglas: Solo se devuelve un libro prestado.", 404, 409, 422);
        app.MapPost("/prestamos/comandos/prestar-un-libro",
            (PrestarUnLibro comando, PrestarUnLibroManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-01: Prestar un libro",
                "Entrada: Lector, libro y plazo del préstamo (desde y hasta).\n\nSalida: Préstamo con su número, en estado prestado.\n\nReglas: REG-01: se rechaza si el catálogo dice que el libro no está disponible.", 404, 409, 422);

        // Consultas: GET con la identidad en la ruta.
        app.MapGet("/prestamos/consultas/consultar-el-prestamo/{numeroDelPrestamo}",
            (string numeroDelPrestamo, ConsultarElPrestamoManejador manejador) => Ejecutar(() => manejador.Manejar(new ConsultarElPrestamo(numeroDelPrestamo))))
            .Documentar<ConsultarElPrestamoSalida>("Consulta SB-03: Consultar el préstamo",
                "Entrada: Número del préstamo.\n\nSalida: Estado del préstamo, lector, libro y fecha en que vence.", 404, 422);


        // Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
        app.MapGet("/prestamos/bitacora", (Bitacora bitacora) => bitacora.Todo())
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
}
