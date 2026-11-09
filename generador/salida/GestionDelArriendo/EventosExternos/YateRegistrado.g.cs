// Generado desde ArchiMate: ApplicationEvent "Yate registrado" (id-4f03a460e265434e87e0081ee5018122).
// Evento de otro contexto (Contexto Disponibilidad de yates) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Yate registrado" de "Contexto Disponibilidad de yates", con los datos que declara el YAML. Se recuerda para los comandos que lo requieren.</summary>
public sealed record YateRegistrado(
    string IdentificadorDelYate,
    string Propietario,
    decimal PrecioPorDia,
    string IdentificadorDeLaMarina
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Yate registrado";

    /// <summary>Identidad con que llega el evento: identificador del yate.</summary>
    public string Identidad => IdentificadorDelYate;
}
