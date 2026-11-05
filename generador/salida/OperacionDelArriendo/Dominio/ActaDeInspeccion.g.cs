// Generado desde ArchiMate: DataObject "Acta de inspección" (id-2856d4f6a4b0480a86d14826dd18dedf).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Raíz "Acta de inspección" del "Agregado Acta de inspección" (id-0af905a47ab94912aef5350558410200).</summary>
public sealed partial class ActaDeInspeccion : IRaiz
{
    /// <summary>Identidad: número del arriendo. Se forma con número del arriendo, separados con "/".</summary>
    public string NumeroDelArriendo { get; private set; } = "";

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDelActaDeInspeccion Estado { get; set; }

    /// <summary>Campo "fotos" (List&lt;string&gt;).</summary>
    public List<string> Fotos { get; set; } = [];

    /// <summary>Campo "nivel de combustible" (decimal).</summary>
    public required decimal NivelDeCombustible { get; set; }

    /// <summary>Campo "hora de regreso" (DateTime).</summary>
    public required DateTime HoraDeRegreso { get; set; }

    /// <summary>Objeto de valor "Daño encontrado", Cardinalidad Muchos (composición id-298e37616e7e4c139b0195ef36ab8ff5).</summary>
    public List<DanoEncontrado> DanoEncontrado { get; set; } = [];

    string IRaiz.Identidad => NumeroDelArriendo;

    void IRaiz.AsignarIdentidad(string identidad) => NumeroDelArriendo = identidad;
}
