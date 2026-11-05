// Generado desde ArchiMate: ApplicationEvent "Lectura registrada" (id-81e0ea1bc1004b88b387861811e7e806).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Evento "Lectura registrada". Lo publica "Registrar lecturas de ubicación y combustible" (SB-25).</summary>
public sealed record LecturaRegistrada(
    string IdentificadorDeLaLectura,
    string IdentificadorDelYate,
    DateTime HoraDeLaLectura
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Lectura registrada";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => IdentificadorDeLaLectura;
}
