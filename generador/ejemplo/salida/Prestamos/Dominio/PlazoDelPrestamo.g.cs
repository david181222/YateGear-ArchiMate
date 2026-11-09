// Generado desde ArchiMate: DataObject "Plazo del préstamo" (id-23f42c26c59a58d4b094e7c17ba625f7).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace Biblioteca.Prestamos;

/// <summary>Objeto de valor "Plazo del préstamo" de la raíz "Préstamo", Cardinalidad Uno.
/// Campos: desde (DateOnly); hasta (DateOnly).</summary>
public sealed record PlazoDelPrestamo(
    DateOnly Desde,
    DateOnly Hasta
);
