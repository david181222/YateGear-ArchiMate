// Generado desde ArchiMate: ApplicationEvent "Reserva cancelada" (id-28e06fd82a7641228d89ded443509b64).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Reserva cancelada". Lo publica "Cancelar la reserva" (SB-08).</summary>
public sealed record ReservaCancelada(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin,
    DateOnly FechaDeLaCancelacion,
    int DiasDeAnticipacion
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Reserva cancelada";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
