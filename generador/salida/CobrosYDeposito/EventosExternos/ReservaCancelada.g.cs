// Generado desde ArchiMate: ApplicationEvent "Reserva cancelada" (id-28e06fd82a7641228d89ded443509b64).
// Evento de otro contexto (Contexto Gestión del arriendo) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Reserva cancelada" de "Contexto Gestión del arriendo", con los datos que declara el YAML. Dispara "Liberar el depósito", "Reembolsar una cancelación".</summary>
public sealed record ReservaCancelada(
    string NumeroDelArriendo,
    DateOnly FechaDeLaCancelacion,
    int DiasDeAnticipacion
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Reserva cancelada";

    /// <summary>Identidad con que llega el evento: número del arriendo.</summary>
    public string Identidad => NumeroDelArriendo;
}
