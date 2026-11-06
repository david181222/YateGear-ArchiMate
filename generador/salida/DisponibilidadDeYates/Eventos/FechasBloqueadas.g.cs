// Generado desde ArchiMate: ApplicationEvent "Fechas bloqueadas" (id-78a96e2310bc4b3e9d6b68b5a56ec4b3).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Evento "Fechas bloqueadas". Lo publica "Definir las fechas bloqueadas del yate" (SB-03).</summary>
public sealed record FechasBloqueadas(
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Fechas bloqueadas";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => IdentificadorDelYate;
}
