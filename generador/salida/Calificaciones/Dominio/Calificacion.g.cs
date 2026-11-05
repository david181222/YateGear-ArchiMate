// Generado desde ArchiMate: DataObject "Calificación" (id-e848e3b4bf284a969c9a0a9d2e4de26f).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.Calificaciones;

/// <summary>Raíz "Calificación" del "Agregado Calificación" (id-b2c84f08d55e4ba0ab2e14427cf5ada9).</summary>
public sealed partial class Calificacion : IRaiz
{
    /// <summary>Identidad: identificador de la calificación. Se forma con número del arriendo, quién califica, separados con "/".</summary>
    public string IdentificadorDeLaCalificacion { get; private set; } = "";

    /// <summary>Parte de la identidad: "número del arriendo" (string).</summary>
    public required string NumeroDelArriendo { get; init; }

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDeLaCalificacion Estado { get; set; }

    /// <summary>Campo "quién califica" (enum Parte que califica(cliente, propietario)).</summary>
    public required ParteQueCalifica QuienCalifica { get; set; }

    /// <summary>Campo "calificación dada" (int).</summary>
    public required int CalificacionDada { get; set; }

    /// <summary>Campo "calificado" (string).</summary>
    public required string Calificado { get; set; }

    string IRaiz.Identidad => IdentificadorDeLaCalificacion;

    void IRaiz.AsignarIdentidad(string identidad) => IdentificadorDeLaCalificacion = identidad;
}
