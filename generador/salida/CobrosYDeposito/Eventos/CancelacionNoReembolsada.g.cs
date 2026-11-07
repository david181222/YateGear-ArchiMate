// Generado desde ArchiMate: ApplicationEvent "Cancelación no reembolsada" (id-498bf53911414b55828987e21aa1aa74).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Cancelación no reembolsada". Lo publica "Reembolsar una cancelación" (SB-15).</summary>
public sealed record CancelacionNoReembolsada(
    string NumeroDelArriendo,
    int DiasDeAnticipacion,
    int DiasMinimosParaElReembolso
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Cancelación no reembolsada";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
