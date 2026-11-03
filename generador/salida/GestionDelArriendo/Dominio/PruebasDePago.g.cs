// Generado desde ArchiMate: DataObject "Pruebas de pago" (id-0c8b1c935dc94f9999ae85d5f779b354).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Objeto de valor "Pruebas de pago" de la raíz "Arriendo", Cardinalidad Cero o uno.
/// Campos: comprobante del alquiler (string); comprobante del seguro (string); autorización del bloqueo del depósito (string).</summary>
public sealed record PruebasDePago(
    string ComprobanteDelAlquiler,
    string ComprobanteDelSeguro,
    string AutorizacionDelBloqueoDelDeposito
);
