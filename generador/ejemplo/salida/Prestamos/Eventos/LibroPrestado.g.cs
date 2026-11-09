// Generado desde ArchiMate: ApplicationEvent "Libro prestado" (id-7808c0a36e435cbeb9af1243ed983bec).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace Biblioteca.Prestamos;

/// <summary>Evento "Libro prestado". Lo publica "Prestar un libro" (SB-01).</summary>
public sealed record LibroPrestado(
    string NumeroDelPrestamo,
    string Lector,
    string Libro,
    DateOnly Hasta
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Libro prestado";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelPrestamo;
}
