// Generado desde ArchiMate: ApplicationEvent "Reserva confirmada" (id-f7f775aec49c4eb782699183059c6bc2).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Reserva confirmada". Lo publica "Confirmar la reserva" (SB-07).</summary>
public sealed record ReservaConfirmada(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Reserva confirmada";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
