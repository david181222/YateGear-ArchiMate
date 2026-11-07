// Generado desde ArchiMate: ApplicationEvent "Diferencias determinadas" (id-497addd0bf144aed8bf9f4ba01d7eac3).
// Evento de otro contexto (Contexto Operación del arriendo) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Diferencias determinadas" de "Contexto Operación del arriendo", con los datos que declara el YAML. Dispara "Liquidar y cobrar los cargos del cierre", "Liberar el depósito", "Descontar daños del depósito".</summary>
public sealed record DiferenciasDeterminadas(
    string NumeroDelArriendo,
    DateTime HoraDeRegreso,
    decimal CombustibleConsumido,
    decimal HorasAdicionales,
    decimal ValorDeLosDanos,
    List<string> Evidencia
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Diferencias determinadas";

    /// <summary>Identidad con que llega el evento: número del arriendo.</summary>
    public string Identidad => NumeroDelArriendo;
}
