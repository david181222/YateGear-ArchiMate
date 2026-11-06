// Generado desde ArchiMate: ApplicationEvent "Cliente calificado" (id-19f69c478e1c47e481a41c991690baaa).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.Calificaciones;

/// <summary>Evento "Cliente calificado". Lo publica "Calificar al cliente" (SB-29).</summary>
public sealed record ClienteCalificado(
    string IdentificadorDeLaCalificacion,
    string Calificado,
    int CalificacionDada
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Cliente calificado";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => IdentificadorDeLaCalificacion;
}
