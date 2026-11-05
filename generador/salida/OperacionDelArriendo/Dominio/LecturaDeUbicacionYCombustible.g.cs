// Generado desde ArchiMate: DataObject "Lectura de ubicación y combustible" (id-6858d99a4eb2404d8c0fce1abfc1d10e).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Raíz "Lectura de ubicación y combustible" del "Agregado Lectura de ubicación y combustible" (id-a60ede1cd8e943f980f2e677828f3d17).</summary>
public sealed partial class LecturaDeUbicacionYCombustible : IRaiz
{
    /// <summary>Identidad: identificador de la lectura. Se forma con identificador del yate, hora de la lectura, separados con "/".</summary>
    public string IdentificadorDeLaLectura { get; private set; } = "";

    /// <summary>Parte de la identidad: "identificador del yate" (string).</summary>
    public required string IdentificadorDelYate { get; init; }

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDeLaLectura Estado { get; set; }

    /// <summary>Campo "latitud" (decimal).</summary>
    public required decimal Latitud { get; set; }

    /// <summary>Campo "longitud" (decimal).</summary>
    public required decimal Longitud { get; set; }

    /// <summary>Campo "nivel de combustible" (decimal).</summary>
    public required decimal NivelDeCombustible { get; set; }

    /// <summary>Campo "hora de la lectura" (DateTime).</summary>
    public required DateTime HoraDeLaLectura { get; set; }

    string IRaiz.Identidad => IdentificadorDeLaLectura;

    void IRaiz.AsignarIdentidad(string identidad) => IdentificadorDeLaLectura = identidad;
}
