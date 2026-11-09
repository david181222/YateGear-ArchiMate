// Generado desde ArchiMate: ApplicationEvent "Yate registrado" (id-4f03a460e265434e87e0081ee5018122).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Evento "Yate registrado". Lo publica "Registrar yate en el inventario" (SB-01).</summary>
public sealed record YateRegistrado(
    string IdentificadorDelYate,
    string Propietario,
    string IdentificadorDeLaMarina,
    decimal PrecioPorDia
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Yate registrado";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => IdentificadorDelYate;
}
