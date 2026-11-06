// Generado desde ArchiMate: ApplicationEvent "Fechas ocupadas" (id-0b4d7ee06e05403ab9022d5232109730).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Evento "Fechas ocupadas". Lo publica "Gestionar la ocupación del calendario" (SB-05).</summary>
public sealed record FechasOcupadas(
    string IdentificadorDelYate,
    string NumeroDelArriendo,
    DateOnly Inicio,
    DateOnly Fin
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Fechas ocupadas";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => IdentificadorDelYate;
}
