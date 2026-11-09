// Generado desde ArchiMate: ApplicationEvent "Depósito bloqueado" (id-41585106baae43ab90ca920de78dc737).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Depósito bloqueado". Lo publica "Bloquear el depósito" (SB-19).</summary>
public sealed record DepositoBloqueado(
    string NumeroDelArriendo,
    string CodigoDeAutorizacionDeLaPasarela,
    DateOnly FechaDeVencimientoDelBloqueo
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Depósito bloqueado";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
