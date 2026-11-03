// Generado desde ArchiMate: ApplicationEvent "Arriendo no realizado por riesgo alto" (id-bb4b23b9412742f89ac3ae34504a8391).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Arriendo no realizado por riesgo alto". Lo publica "Obtener el nivel de riesgo del cliente" (SB-12).</summary>
public sealed record ArriendoNoRealizadoPorRiesgoAlto(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Arriendo no realizado por riesgo alto";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
