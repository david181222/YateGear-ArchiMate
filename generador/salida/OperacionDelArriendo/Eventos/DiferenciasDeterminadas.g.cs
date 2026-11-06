// Generado desde ArchiMate: ApplicationEvent "Diferencias determinadas" (id-497addd0bf144aed8bf9f4ba01d7eac3).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Evento "Diferencias determinadas". Lo publica "Determinar las diferencias entre entrega y devolución" (SB-24).</summary>
public sealed record DiferenciasDeterminadas(
    string NumeroDelArriendo,
    decimal CombustibleConsumido,
    decimal HorasAdicionales,
    decimal ValorDeLosDanos
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Diferencias determinadas";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
