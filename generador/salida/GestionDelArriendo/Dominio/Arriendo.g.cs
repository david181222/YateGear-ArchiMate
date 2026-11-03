// Generado desde ArchiMate: DataObject "Arriendo" (id-3f15410f516e4820b86108f1896461a8).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Raíz "Arriendo" del "Agregado Arriendo" (id-2b918a7081b74d8a96e6112d86f829c1).</summary>
public sealed partial class Arriendo : IRaiz
{
    /// <summary>Identidad: número del arriendo. La asigna el repositorio al guardar (ARR-0001, ...).</summary>
    public string NumeroDelArriendo { get; private set; } = "";

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDelArriendo Estado { get; set; }

    /// <summary>Campo "referencia del contrato firmado" (string?).</summary>
    public string? ReferenciaDelContratoFirmado { get; set; }

    /// <summary>Objeto de valor "Evaluación de riesgo", Cardinalidad Cero o uno (composición id-e5367ed813444b918401bd1f57d029b1).</summary>
    public EvaluacionDeRiesgo? EvaluacionDeRiesgo { get; set; }

    /// <summary>Objeto de valor "Fechas del arriendo", Cardinalidad Uno (composición id-ee06d268da2f408d8bf9bde7bb305334).</summary>
    public required FechasDelArriendo FechasDelArriendo { get; set; }

    /// <summary>Objeto de valor "Ficha del cliente", Cardinalidad Uno (composición id-ad7757e40c604c82b7b1f65e724cf4d7).</summary>
    public required FichaDelCliente FichaDelCliente { get; set; }

    /// <summary>Objeto de valor "Pruebas de pago", Cardinalidad Cero o uno (composición id-da20b204b668426dbba89a9cd13ce8f3).</summary>
    public PruebasDePago? PruebasDePago { get; set; }

    /// <summary>Objeto de valor "Yate del arriendo", Cardinalidad Uno (composición id-850fc88d230048ef9cb724ee440e7d42).</summary>
    public required YateDelArriendo YateDelArriendo { get; set; }

    string IRaiz.Identidad => NumeroDelArriendo;

    void IRaiz.AsignarIdentidad(string identidad) => NumeroDelArriendo = identidad;
}
