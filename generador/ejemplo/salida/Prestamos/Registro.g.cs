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
            (DevolverElLibro comando, DevolverElLibroManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/prestamos/comandos/prestar-un-libro",
            (PrestarUnLibro comando, PrestarUnLibroManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));

        // Consultas: GET con la identidad en la ruta.
        app.MapGet("/prestamos/consultas/consultar-el-prestamo/{numeroDelPrestamo}",
            (string numeroDelPrestamo, ConsultarElPrestamoManejador manejador) => Ejecutar(() => manejador.Manejar(new ConsultarElPrestamo(numeroDelPrestamo))));


        // Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
        app.MapGet("/prestamos/bitacora", (Bitacora bitacora) => bitacora.Todo());
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
