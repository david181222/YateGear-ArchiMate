// Generado desde ArchiMate: ApplicationEvent "Reserva solicitada" (id-ba01aa1a0874474086ba64badf2991e3).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Reserva solicitada". Lo publica "Registrar la solicitud de reserva" (SB-06).</summary>
public sealed record ReservaSolicitada(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Reserva solicitada";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
