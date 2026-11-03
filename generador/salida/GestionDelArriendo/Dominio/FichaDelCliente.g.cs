// Generado desde ArchiMate: DataObject "Ficha del cliente" (id-a1609e0b86274fad86e6159ddec11f8b).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Objeto de valor "Ficha del cliente" de la raíz "Arriendo", Cardinalidad Uno.
/// Campos: referencia al CRM (string); número de la licencia (string); vigencia de la licencia (DateOnly); fecha de la autorización (DateOnly); terceros autorizados (List&lt;string&gt;).</summary>
public sealed record FichaDelCliente(
    string ReferenciaAlCRM,
    string NumeroDeLaLicencia,
    DateOnly VigenciaDeLaLicencia,
    DateOnly FechaDeLaAutorizacion,
    List<string> TercerosAutorizados
);
