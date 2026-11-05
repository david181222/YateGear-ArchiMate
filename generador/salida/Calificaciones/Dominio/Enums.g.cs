// Generado desde ArchiMate: ApplicationComponent "Contexto Calificaciones" (id-6f29abc193cb4f2fa1234cec80bf0675).
// Enums del contexto, de los campos del modelo y del YAML. No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.Calificaciones;

/// <summary>Enum "Estado de la calificación". Se usa en: estado de la raíz "Calificación" (YAML).</summary>
public enum EstadoDeLaCalificacion
{
    /// <summary>registrada</summary>
    Registrada,
}

/// <summary>Enum "Parte que califica". Se usa en: campo "quién califica" de "Calificación" (id-e848e3b4bf284a969c9a0a9d2e4de26f).</summary>
public enum ParteQueCalifica
{
    /// <summary>cliente</summary>
    Cliente,
    /// <summary>propietario</summary>
    Propietario,
}
