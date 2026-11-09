// Generado desde ArchiMate: ApplicationProcess "Prestar un libro" (SB-01, id-adbef6a6733f58f5a9e0ba51f136a4ac).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en PrestarUnLibro.cs.
#nullable enable
namespace Biblioteca.Prestamos;

/// <summary>Entrada del comando "Prestar un libro" (SB-01).</summary>
public sealed record PrestarUnLibro(
    string Lector,
    string Libro,
    DateOnly Desde,
    DateOnly Hasta
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record PrestarUnLibroDatos(
    PrestarUnLibro Comando,
    CatalogoDeLaBibliotecaSalida CatalogoDeLaBiblioteca
);

/// <summary>Manejador del comando "Prestar un libro" (SB-01).</summary>
/// <remarks>
/// <para>Contrato de servicio: Prestar un libro (id-ae3bbf116893597ab208483228f70381), asociado al servicio de negocio
/// "Prestar un libro" (id-2c4ab840149c5f6bb997fd138b8d7665), que el comando realiza.</para>
/// <para>Entrada: Lector, libro y plazo del préstamo (desde y hasta).</para>
/// <para>Salida: Préstamo con su número, en estado prestado.</para>
/// <para>Reglas: REG-01: se rechaza si el catálogo dice que el libro no está disponible. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class PrestarUnLibroManejador(
    Repositorio<Prestamo> repositorio,
    BusDeEventos bus,
    ICatalogoDeLaBiblioteca catalogoDeLaBiblioteca
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(PrestarUnLibroDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(PrestarUnLibro comando)
    {
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 2. Servicios SA que usa, en orden.
        var respuestaCatalogoDeLaBiblioteca = catalogoDeLaBiblioteca.Llamar(new CatalogoDeLaBibliotecaEntrada(comando.Libro));

        // 4. Reglas del contrato (archivo manual).
        var datos = new PrestarUnLibroDatos(comando, respuestaCatalogoDeLaBiblioteca);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Al guardarla recibe su identidad.
        var prestamo = new Prestamo
        {
            Estado = EstadoDelPrestamo.Prestado,
            Lector = comando.Lector,
            Libro = comando.Libro,
            PlazoDelPrestamo = new PlazoDelPrestamo(comando.Desde, comando.Hasta),
        };
        repositorio.Guardar(prestamo);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new LibroPrestado(prestamo.NumeroDelPrestamo, comando.Lector, comando.Libro, comando.Hasta), eventos);
        return new RespuestaDeComando(prestamo.NumeroDelPrestamo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
