// Generado desde ArchiMate: ApplicationEvent "Libro devuelto" (id-4baadb7858ae500cb39ea7b0dc99f59c).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace Biblioteca.Prestamos;

/// <summary>Evento "Libro devuelto". Lo publica "Devolver el libro" (SB-02).</summary>
public sealed record LibroDevuelto(
    string NumeroDelPrestamo,
    string Libro
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Libro devuelto";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelPrestamo;
}
