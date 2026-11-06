// Generado desde ArchiMate: DataObject "Acta de entrega" (id-f4fb995872c5435f8ccb7e85e17cbee9).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Raíz "Acta de entrega" del "Agregado Acta de entrega" (id-cba36345d0664e588345d53208c936f0).</summary>
public sealed partial class ActaDeEntrega : IRaiz
{
    /// <summary>Identidad: número del arriendo. Se forma con número del arriendo, separados con "/".</summary>
    public string NumeroDelArriendo { get; private set; } = "";

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDelActaDeEntrega Estado { get; set; }

    /// <summary>Campo "fotos" (List&lt;string&gt;).</summary>
    public List<string> Fotos { get; set; } = [];

    /// <summary>Campo "nivel de combustible" (decimal).</summary>
    public required decimal NivelDeCombustible { get; set; }

    /// <summary>Campo "hora de entrega" (DateTime).</summary>
    public required DateTime HoraDeEntrega { get; set; }

    /// <summary>Campo "observaciones" (string?).</summary>
    public string? Observaciones { get; set; }

    /// <summary>Campo "identificador del yate" (string).</summary>
    public required string IdentificadorDelYate { get; set; }

    string IRaiz.Identidad => NumeroDelArriendo;

    void IRaiz.AsignarIdentidad(string identidad) => NumeroDelArriendo = identidad;
}
