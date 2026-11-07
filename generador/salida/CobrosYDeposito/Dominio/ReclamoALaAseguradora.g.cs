// Generado desde ArchiMate: DataObject "Reclamo a la aseguradora" (id-97138119487d4fa1aa1837e907129ad1).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Raíz "Reclamo a la aseguradora" del "Agregado Reclamo a la aseguradora" (id-cf6ab73466b745f2ab2bdad9fefcb87c).</summary>
public sealed partial class ReclamoALaAseguradora : IRaiz
{
    /// <summary>Identidad: número de reclamo. La asigna el repositorio al guardar (REC-0001, ...).</summary>
    public string NumeroDeReclamo { get; private set; } = "";

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDelReclamo Estado { get; set; }

    /// <summary>Campo "identificador del arriendo" (string).</summary>
    public required string IdentificadorDelArriendo { get; set; }

    /// <summary>Campo "número de póliza" (string).</summary>
    public required string NumeroDePoliza { get; set; }

    /// <summary>Campo "valor de los daños" (decimal).</summary>
    public required decimal ValorDeLosDanos { get; set; }

    /// <summary>Campo "valor descontado del depósito" (decimal).</summary>
    public required decimal ValorDescontadoDelDeposito { get; set; }

    /// <summary>Campo "evidencia" (List&lt;string&gt;).</summary>
    public List<string> Evidencia { get; set; } = [];

    string IRaiz.Identidad => NumeroDeReclamo;

    void IRaiz.AsignarIdentidad(string identidad) => NumeroDeReclamo = identidad;
}
