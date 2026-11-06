// Generado desde ArchiMate: ApplicationEvent "Arriendo cerrado" (id-0f65cc3ebf6649e283d9b634febb03f5).
// Evento de otro contexto (Contexto Gestión del arriendo) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.Calificaciones;

/// <summary>Evento "Arriendo cerrado" de "Contexto Gestión del arriendo", con los datos que declara el YAML. Se recuerda para los comandos que lo requieren.</summary>
public sealed record ArriendoCerrado(
    string NumeroDelArriendo,
    string ReferenciaAlCRM,
    string Propietario,
    DateTime FechaYHoraDelCambio
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Arriendo cerrado";

    /// <summary>Identidad con que llega el evento: número del arriendo.</summary>
    public string Identidad => NumeroDelArriendo;
}
