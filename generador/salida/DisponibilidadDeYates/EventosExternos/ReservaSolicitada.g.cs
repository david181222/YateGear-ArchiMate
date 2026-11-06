// Generado desde ArchiMate: ApplicationEvent "Reserva solicitada" (id-ba01aa1a0874474086ba64badf2991e3).
// Evento de otro contexto (Contexto Gestión del arriendo) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Evento "Reserva solicitada" de "Contexto Gestión del arriendo", con los datos que declara el YAML. Dispara "Gestionar la ocupación del calendario".</summary>
public sealed record ReservaSolicitada(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Reserva solicitada";

    /// <summary>Identidad con que llega el evento: número del arriendo.</summary>
    public string Identidad => NumeroDelArriendo;
}
