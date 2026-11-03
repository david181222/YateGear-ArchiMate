// Generado desde ArchiMate: DataObject "Fechas del arriendo" (id-9bedd8cb487b46b199f02d88287ac768).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Objeto de valor "Fechas del arriendo" de la raíz "Arriendo", Cardinalidad Uno.
/// Campos: inicio (DateOnly); fin (DateOnly).</summary>
public sealed record FechasDelArriendo(
    DateOnly Inicio,
    DateOnly Fin
);
