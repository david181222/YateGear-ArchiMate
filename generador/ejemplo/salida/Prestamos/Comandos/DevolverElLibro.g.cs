// Generado desde ArchiMate: ApplicationProcess "Devolver el libro" (SB-02, id-5bf799b38b425df3b814b33aa2929f70).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en DevolverElLibro.cs.
#nullable enable
namespace Biblioteca.Prestamos;

/// <summary>Entrada del comando "Devolver el libro" (SB-02).</summary>
public sealed record DevolverElLibro(
    string NumeroDelPrestamo
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record DevolverElLibroDatos(
    DevolverElLibro Comando,
    Prestamo Prestamo
);

/// <summary>Manejador del comando "Devolver el libro" (SB-02).</summary>
/// <remarks>
/// <para>Contrato de servicio: Devolver el libro (id-be012cf9cf7a573c8176e8e3dadd4814), asociado al servicio de negocio
/// "Devolver el libro" (id-48151143e7315060b5a0ceed638aadcf), que el comando realiza.</para>
/// <para>Entrada: Número del préstamo.</para>
/// <para>Salida: Préstamo devuelto.</para>
/// <para>Reglas: Solo se devuelve un libro prestado. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class DevolverElLibroManejador(
    Repositorio<Prestamo> repositorio,
    BusDeEventos bus
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(DevolverElLibroDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(DevolverElLibro comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelPrestamo)) throw new DatoFaltante("número del préstamo");
        // 1. Cargar la raíz.
        var prestamo = repositorio.Obtener(comando.NumeroDelPrestamo)
            ?? throw new NoEncontrado($"No existe préstamo {comando.NumeroDelPrestamo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Devolver el libro", prestamo.Estado, EstadoDelPrestamo.Prestado);

        // 4. Reglas del contrato (archivo manual).
        var datos = new DevolverElLibroDatos(comando, prestamo);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        prestamo.Estado = EstadoDelPrestamo.Devuelto;
        repositorio.Guardar(prestamo);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new LibroDevuelto(prestamo.NumeroDelPrestamo, prestamo.Libro), eventos);
        return new RespuestaDeComando(prestamo.NumeroDelPrestamo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
