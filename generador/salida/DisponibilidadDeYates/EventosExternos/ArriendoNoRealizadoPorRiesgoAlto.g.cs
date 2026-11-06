// Generado desde ArchiMate: ApplicationEvent "Arriendo no realizado por riesgo alto" (id-bb4b23b9412742f89ac3ae34504a8391).
// Evento de otro contexto (Contexto Gestión del arriendo) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Evento "Arriendo no realizado por riesgo alto" de "Contexto Gestión del arriendo", con los datos que declara el YAML. Dispara "Gestionar la ocupación del calendario".</summary>
public sealed record ArriendoNoRealizadoPorRiesgoAlto(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Arriendo no realizado por riesgo alto";

    /// <summary>Identidad con que llega el evento: número del arriendo.</summary>
    public string Identidad => NumeroDelArriendo;
}
