// Generado desde ArchiMate: ApplicationEvent "Yate devuelto" (id-8efeaef2f23441879f0f9fe08fb63a2e).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Yate devuelto". Lo publica "Registrar el avance del arriendo" (SB-09).</summary>
public sealed record YateDevuelto(
    string NumeroDelArriendo,
    DateTime FechaYHoraDelCambio
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Yate devuelto";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
