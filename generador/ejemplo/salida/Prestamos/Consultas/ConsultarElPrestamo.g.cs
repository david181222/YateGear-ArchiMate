// Generado desde ArchiMate: ApplicationService "Consultar el préstamo" (SB-03, id-b3770e1c734d569ca65ced6e4d6ce41a).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en ConsultarElPrestamo.cs.
#nullable enable
namespace Biblioteca.Prestamos;

/// <summary>Entrada de la consulta "Consultar el préstamo" (SB-03).</summary>
public sealed record ConsultarElPrestamo(
    string NumeroDelPrestamo
);

/// <summary>Salida de la consulta "Consultar el préstamo".</summary>
public sealed record ConsultarElPrestamoSalida(
    EstadoDelPrestamo Estado,
    string Lector,
    string Libro,
    DateOnly Hasta
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: la consulta y la raíz.</summary>
public sealed record ConsultarElPrestamoDatos(ConsultarElPrestamo Consulta, Prestamo Prestamo);

/// <summary>Manejador de la consulta "Consultar el préstamo" (SB-03). No cambia la raíz.</summary>
/// <remarks>
/// <para>Contrato de servicio: Consultar el préstamo (id-1eb53a4c5895511dba1b123b4317670e), asociado al servicio de negocio
/// "Consultar el préstamo" (id-a17fb94b9d105e6cb5ec8095d9d61062).</para>
/// <para>Entrada: Número del préstamo.</para>
/// <para>Salida: Estado del préstamo, lector, libro y fecha en que vence.</para>
/// <para>Reglas: el contrato no tiene reglas. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class ConsultarElPrestamoManejador(Repositorio<Prestamo> repositorio)
{
    /// <summary>Reglas del contrato. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(ConsultarElPrestamoDatos datos);

    /// <summary>Ejecuta la consulta.</summary>
    public ConsultarElPrestamoSalida Manejar(ConsultarElPrestamo consulta)
    {
        var prestamo = repositorio.Obtener(consulta.NumeroDelPrestamo)
            ?? throw new NoEncontrado($"No existe préstamo {consulta.NumeroDelPrestamo}.");
        var datos = new ConsultarElPrestamoDatos(consulta, prestamo);
        ValidarReglas(datos);
        return new ConsultarElPrestamoSalida(
            prestamo.Estado,
            prestamo.Lector,
            prestamo.Libro,
            prestamo.PlazoDelPrestamo.Hasta
        );
    }
}
