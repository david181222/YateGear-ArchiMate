// Generado desde ArchiMate: ApplicationEvent "Pérdida de señal del yate" (id-f8aec7f1160d42d4994bba6dc64d04ab).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Evento "Pérdida de señal del yate". Lo publica "Detectar la pérdida de señal" (SB-27).</summary>
public sealed record PerdidaDeSenalDelYate(
    string IdentificadorDeLaLectura,
    string IdentificadorDelYate,
    decimal Latitud,
    decimal Longitud,
    decimal NivelDeCombustible,
    DateTime HoraDeLaLectura
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Pérdida de señal del yate";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => IdentificadorDeLaLectura;
}
