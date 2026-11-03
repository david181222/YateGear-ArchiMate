// Generado desde ArchiMate: ApplicationEvent "Arriendo cerrado" (id-0f65cc3ebf6649e283d9b634febb03f5).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Arriendo cerrado". Lo publica "Registrar el avance del arriendo" (SB-09).</summary>
public sealed record ArriendoCerrado(
    string NumeroDelArriendo,
    string ReferenciaAlCRM,
    string Propietario,
    DateTime FechaYHoraDelCambio
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Arriendo cerrado";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
