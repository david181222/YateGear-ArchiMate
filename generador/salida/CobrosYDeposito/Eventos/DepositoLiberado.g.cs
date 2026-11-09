// Generado desde ArchiMate: ApplicationEvent "Depósito liberado" (id-6128af9686a2416bada40d02108bce05).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Depósito liberado". Lo publica "Liberar el depósito" (SB-20).</summary>
public sealed record DepositoLiberado(
    string NumeroDelArriendo,
    decimal ValorDelDeposito,
    DateOnly FechaDeLaLiberacion
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Depósito liberado";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
