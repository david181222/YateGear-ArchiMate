// Generado desde ArchiMate: ApplicationEvent "Reserva confirmada" (id-f7f775aec49c4eb782699183059c6bc2).
// Evento de otro contexto (Contexto Gestión del arriendo) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Evento "Reserva confirmada" de "Contexto Gestión del arriendo", con los datos que declara el YAML. Se recuerda para los comandos que lo requieren.</summary>
public sealed record ReservaConfirmada(
    string NumeroDelArriendo,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Reserva confirmada";

    /// <summary>Identidad con que llega el evento: número del arriendo.</summary>
    public string Identidad => NumeroDelArriendo;
}
