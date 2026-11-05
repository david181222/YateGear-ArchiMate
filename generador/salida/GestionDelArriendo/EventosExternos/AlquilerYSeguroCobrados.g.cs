// Generado desde ArchiMate: ApplicationEvent "Alquiler y seguro cobrados" (id-a5729d322f444202bc1a34c7d68a46d8).
// Evento de otro contexto (Contexto Cobros y depósito) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Alquiler y seguro cobrados" de "Contexto Cobros y depósito", con los datos que declara el YAML. Dispara "Confirmar la reserva".</summary>
public sealed record AlquilerYSeguroCobrados(
    string NumeroDelArriendo,
    string ComprobanteDelAlquiler,
    string ComprobanteDelSeguro
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Alquiler y seguro cobrados";

    /// <summary>Identidad con que llega el evento: número del arriendo.</summary>
    public string Identidad => NumeroDelArriendo;
}
