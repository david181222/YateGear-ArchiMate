// Generado desde ArchiMate: ApplicationEvent "Aviso de reserva enviado" (id-b65aec8c4e0641b0ac0ef6c69373610f).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Aviso de reserva enviado". Lo publica "Enviar el aviso de reserva confirmada" (SB-31).</summary>
public sealed record AvisoDeReservaEnviado(
    string NumeroDelArriendo,
    string ConstanciaDelAviso
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Aviso de reserva enviado";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
