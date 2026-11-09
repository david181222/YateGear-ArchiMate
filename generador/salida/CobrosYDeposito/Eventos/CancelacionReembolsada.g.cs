// Generado desde ArchiMate: ApplicationEvent "Cancelación reembolsada" (id-09c2a90d529d4de08b38adea6ab20ce0).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Cancelación reembolsada". Lo publica "Reembolsar una cancelación" (SB-15).</summary>
public sealed record CancelacionReembolsada(
    string NumeroDelArriendo,
    decimal ValorDelReembolso,
    string ComprobanteDelReembolso
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Cancelación reembolsada";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
