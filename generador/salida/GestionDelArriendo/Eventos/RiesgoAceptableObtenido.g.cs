// Generado desde ArchiMate: ApplicationEvent "Riesgo aceptable obtenido" (id-898e6b49f085471cb23b1ef1dbaa953e).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Riesgo aceptable obtenido". Lo publica "Obtener el nivel de riesgo del cliente" (SB-12).</summary>
public sealed record RiesgoAceptableObtenido(
    string NumeroDelArriendo,
    string ReferenciaAlCRM,
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin,
    decimal PrecioPorDia
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Riesgo aceptable obtenido";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
