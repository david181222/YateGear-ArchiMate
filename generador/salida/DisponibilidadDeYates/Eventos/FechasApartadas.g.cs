// Generado desde ArchiMate: ApplicationEvent "Fechas apartadas" (id-314372c86c5e4e1981862bfbc8243d35).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Evento "Fechas apartadas". Lo publica "Gestionar la ocupación del calendario" (SB-05).</summary>
public sealed record FechasApartadas(
    string IdentificadorDelYate,
    string NumeroDelArriendo,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Fechas apartadas";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => IdentificadorDelYate;
}
