// Generado desde ArchiMate: ApplicationEvent "Reserva cancelada" (id-28e06fd82a7641228d89ded443509b64).
// Evento de otro contexto (Contexto Gestión del arriendo) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Evento "Reserva cancelada" de "Contexto Gestión del arriendo", con los datos que declara el YAML. Dispara "Gestionar la ocupación del calendario".</summary>
public sealed record ReservaCancelada(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Reserva cancelada";

    /// <summary>Identidad con que llega el evento: número del arriendo.</summary>
    public string Identidad => NumeroDelArriendo;
}
