// Generado desde ArchiMate: ApplicationEvent "Arriendo iniciado" (id-6d63b57590714cd5a0c45b5f6e7b9580).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Arriendo iniciado". Lo publica "Registrar el avance del arriendo" (SB-09).</summary>
public sealed record ArriendoIniciado(
    string NumeroDelArriendo,
    DateTime FechaYHoraDelCambio
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Arriendo iniciado";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
