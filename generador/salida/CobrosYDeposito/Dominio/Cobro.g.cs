// Generado desde ArchiMate: DataObject "Cobro" (id-73b07f4ddacf4826ad340226a0e59119).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entidad "Cobro" de la raíz "Cuenta del arriendo", Cardinalidad Muchos (G9). Su identidad
/// dentro de la raíz es "comprobante": la raíz no admite dos con la misma.
/// Campos: concepto (enum Concepto del cobro(alquiler, seguro, combustible consumido, tiempo adicional, reembolso)); valor (decimal); comprobante (string); evidencia (List&lt;string&gt;); fecha (DateOnly).</summary>
public sealed record Cobro(
    ConceptoDelCobro Concepto,
    decimal Valor,
    string Comprobante,
    List<string> Evidencia,
    DateOnly Fecha
) : IEntidad
{
    /// <summary>Identidad de la entidad dentro de su raíz: "comprobante".</summary>
    string IEntidad.Identidad => Comprobante;
}
