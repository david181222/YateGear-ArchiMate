// Generado desde ArchiMate: DataObject "Yate del arriendo" (id-786fdd755c774038ad7b0d1d163a5d63).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Objeto de valor "Yate del arriendo" de la raíz "Arriendo", Cardinalidad Uno.
/// Campos: identificador del yate (string); propietario (string); precio por día (decimal); marina (string).</summary>
public sealed record YateDelArriendo(
    string IdentificadorDelYate,
    string Propietario,
    decimal PrecioPorDia,
    string Marina
);
