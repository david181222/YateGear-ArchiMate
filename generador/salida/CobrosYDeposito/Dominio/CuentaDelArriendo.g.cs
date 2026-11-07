// Generado desde ArchiMate: DataObject "Cuenta del arriendo" (id-cc25b8b2503f4df286f2f28f1c7ab12b).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Raíz "Cuenta del arriendo" del "Agregado Cuenta del arriendo" (id-061a58e9c8b548bc9990fbd624423929).</summary>
public sealed partial class CuentaDelArriendo : IRaiz
{
    /// <summary>Identidad: número del arriendo. Se forma con número del arriendo, separados con "/".</summary>
    public string NumeroDelArriendo { get; private set; } = "";

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDeLaCuenta Estado { get; set; }

    /// <summary>Campo "identificador del yate" (string).</summary>
    public required string IdentificadorDelYate { get; set; }

    /// <summary>Campo "propietario" (string).</summary>
    public required string Propietario { get; set; }

    /// <summary>Campo "comisión" (decimal?).</summary>
    public decimal? Comision { get; set; }

    /// <summary>Campo "valor del propietario" (decimal?).</summary>
    public decimal? ValorDelPropietario { get; set; }

    /// <summary>Entidad "Cobro", Cardinalidad Muchos (composición id-1acf1b6581c64b4dbe084ec858fe4fa8).</summary>
    public List<Cobro> Cobro { get; set; } = [];

    /// <summary>Objeto de valor "Póliza del arriendo", Cardinalidad Cero o uno (composición id-5e8f9c1b956f4633bf927c03a598d9fa).</summary>
    public PolizaDelArriendo? PolizaDelArriendo { get; set; }

    string IRaiz.Identidad => NumeroDelArriendo;

    void IRaiz.AsignarIdentidad(string identidad) => NumeroDelArriendo = identidad;
}
