// Generado desde ArchiMate: DataObject "Préstamo" (id-8fc36207505e52cc9ef19a99e47dfca7).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace Biblioteca.Prestamos;

/// <summary>Raíz "Préstamo" del "Agregado Préstamo" (id-94a54a4626ed53a3bea811adf0f8258a).</summary>
public sealed partial class Prestamo : IRaiz
{
    /// <summary>Identidad: número del préstamo. La asigna el repositorio al guardar (PRE-0001, ...).</summary>
    public string NumeroDelPrestamo { get; private set; } = "";

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDelPrestamo Estado { get; set; }

    /// <summary>Campo "lector" (string).</summary>
    public required string Lector { get; set; }

    /// <summary>Campo "libro" (string).</summary>
    public required string Libro { get; set; }

    /// <summary>Objeto de valor "Plazo del préstamo", Cardinalidad Uno (composición id-86bfa95f526f5a4b8ccf361274067d5f).</summary>
    public required PlazoDelPrestamo PlazoDelPrestamo { get; set; }

    string IRaiz.Identidad => NumeroDelPrestamo;

    void IRaiz.AsignarIdentidad(string identidad) => NumeroDelPrestamo = identidad;
}
