// Generado desde ArchiMate: ApplicationEvent "Fechas desbloqueadas" (id-d6d1cd177abd4faf9f86763960b16584).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Evento "Fechas desbloqueadas". Lo publica "Definir las fechas bloqueadas del yate" (SB-03).</summary>
public sealed record FechasDesbloqueadas(
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Fechas desbloqueadas";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => IdentificadorDelYate;
}
