// Generado desde ArchiMate: ApplicationEvent "Daños descontados del depósito" (id-20ea85b6df0f4664a60ff0b1b19a222e).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Daños descontados del depósito". Lo publica "Descontar daños del depósito" (SB-21).</summary>
public sealed record DanosDescontadosDelDeposito(
    string NumeroDelArriendo,
    decimal ValorDeLosDanos,
    decimal ValorDescontadoDelDeposito,
    decimal SaldoLiberado,
    decimal ValorQueExcedeElDeposito,
    List<string> Evidencia
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Daños descontados del depósito";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
