// Generado desde ArchiMate: ApplicationEvent "Fechas liberadas" (id-d9533d434fc748f18cada63f170e4319).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Evento "Fechas liberadas". Lo publica "Gestionar la ocupación del calendario" (SB-05).</summary>
public sealed record FechasLiberadas(
    string IdentificadorDelYate,
    string NumeroDelArriendo,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Fechas liberadas";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => IdentificadorDelYate;
}
