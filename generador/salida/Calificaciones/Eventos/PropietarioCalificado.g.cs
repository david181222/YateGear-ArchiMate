// Generado desde ArchiMate: ApplicationEvent "Propietario calificado" (id-7680477f87b2487f8c2af8de885a11de).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.Calificaciones;

/// <summary>Evento "Propietario calificado". Lo publica "Calificar al propietario" (SB-28).</summary>
public sealed record PropietarioCalificado(
    string IdentificadorDeLaCalificacion,
    string Calificado,
    int CalificacionDada
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Propietario calificado";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => IdentificadorDeLaCalificacion;
}
