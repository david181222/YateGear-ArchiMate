// Generado desde ArchiMate: DataObject "Depósito para daños" (id-6545ac90ecf249a4b622c562c49eeeca).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Raíz "Depósito para daños" del "Agregado Depósito para daños" (id-201299ead2af4e15b951240a3ff4586c).</summary>
public sealed partial class DepositoParaDanos : IRaiz
{
    /// <summary>Identidad: número del arriendo. Se forma con número del arriendo, separados con "/".</summary>
    public string NumeroDelArriendo { get; private set; } = "";

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDelDeposito Estado { get; set; }

    /// <summary>Campo "valor del depósito" (decimal).</summary>
    public required decimal ValorDelDeposito { get; set; }

    /// <summary>Campo "código de autorización de la pasarela" (string).</summary>
    public required string CodigoDeAutorizacionDeLaPasarela { get; set; }

    /// <summary>Campo "fecha de vencimiento del bloqueo" (DateOnly).</summary>
    public required DateOnly FechaDeVencimientoDelBloqueo { get; set; }

    /// <summary>Campo "evidencia del descuento" (List&lt;string&gt;).</summary>
    public List<string> EvidenciaDelDescuento { get; set; } = [];

    string IRaiz.Identidad => NumeroDelArriendo;

    void IRaiz.AsignarIdentidad(string identidad) => NumeroDelArriendo = identidad;
}
