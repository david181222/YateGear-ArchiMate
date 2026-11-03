// Generado desde ArchiMate: DataObject "Evaluación de riesgo" (id-f821ca9b471a410dbf6859cd50f53ce9).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Objeto de valor "Evaluación de riesgo" de la raíz "Arriendo", Cardinalidad Cero o uno.
/// Campos: nivel (enum Nivel de riesgo(bajo, medio, alto)); fecha (DateOnly).</summary>
public sealed record EvaluacionDeRiesgo(
    NivelDeRiesgo Nivel,
    DateOnly Fecha
);
