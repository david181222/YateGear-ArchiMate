// Generado desde ArchiMate: DataObject "Yate" (id-d50ced5f46a849f7b744fc977ab040e9).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Raíz "Yate" del "Agregado Yate" (id-50ce3b21f9bf46de85846efc0fadda0a).</summary>
public sealed partial class Yate : IRaiz
{
    /// <summary>Identidad: identificador del yate. La asigna el repositorio al guardar (YATE-0001, ...).</summary>
    public string IdentificadorDelYate { get; private set; } = "";

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDelYate Estado { get; set; }

    /// <summary>Campo "propietario" (string).</summary>
    public required string Propietario { get; set; }

    /// <summary>Campo "precio por día" (decimal).</summary>
    public required decimal PrecioPorDia { get; set; }

    /// <summary>Campo "documentos al día ante la DIMAR" (bool).</summary>
    public required bool DocumentosAlDiaAnteLaDIMAR { get; set; }

    /// <summary>Campo "referencia del contrato del propietario" (string).</summary>
    public required string ReferenciaDelContratoDelPropietario { get; set; }

    /// <summary>Campo "identificador de la marina" (string).</summary>
    public required string IdentificadorDeLaMarina { get; set; }

    /// <summary>Objeto de valor "Datos del yate", Cardinalidad Uno (composición id-6094d0d152164f9299f3ebd575b7c810).</summary>
    public required DatosDelYate DatosDelYate { get; set; }

    string IRaiz.Identidad => IdentificadorDelYate;

    void IRaiz.AsignarIdentidad(string identidad) => IdentificadorDelYate = identidad;
}
