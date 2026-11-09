// Generado desde ArchiMate: ApplicationEvent "Alquiler y seguro cobrados" (id-a5729d322f444202bc1a34c7d68a46d8).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Alquiler y seguro cobrados". Lo publica "Cobrar alquiler y seguro" (SB-13).</summary>
public sealed record AlquilerYSeguroCobrados(
    string NumeroDelArriendo,
    string ComprobanteDelAlquiler,
    string ComprobanteDelSeguro
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Alquiler y seguro cobrados";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
