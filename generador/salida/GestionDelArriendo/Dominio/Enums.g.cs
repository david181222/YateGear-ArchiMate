// Generado desde ArchiMate: ApplicationComponent "Contexto Gestión del arriendo" (id-fdcc9b19f08a492f8ccd5dd4559926bc).
// Enums del contexto, de los campos del modelo y del YAML. No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Enum "Avance del arriendo". Se usa en: entrada de "Registrar el avance del arriendo" (YAML).</summary>
public enum AvanceDelArriendo
{
    /// <summary>en curso</summary>
    EnCurso,
    /// <summary>devuelto</summary>
    Devuelto,
    /// <summary>cerrado</summary>
    Cerrado,
}

/// <summary>Enum "Estado del arriendo". Se usa en: estado de la raíz "Arriendo" (YAML); salida de "Consultar el arriendo" (YAML).</summary>
public enum EstadoDelArriendo
{
    /// <summary>reserva solicitada</summary>
    ReservaSolicitada,
    /// <summary>reserva confirmada</summary>
    ReservaConfirmada,
    /// <summary>no realizado por riesgo alto</summary>
    NoRealizadoPorRiesgoAlto,
    /// <summary>cancelado</summary>
    Cancelado,
    /// <summary>en curso</summary>
    EnCurso,
    /// <summary>devuelto</summary>
    Devuelto,
    /// <summary>cerrado</summary>
    Cerrado,
}

/// <summary>Enum "Estado del contrato". Se usa en: salida de "Contratos con propietarios y clientes" (YAML).</summary>
public enum EstadoDelContrato
{
    /// <summary>enviado</summary>
    Enviado,
    /// <summary>firmado</summary>
    Firmado,
}

/// <summary>Enum "Nivel de riesgo". Se usa en: campo "nivel" de "Evaluación de riesgo" (id-f821ca9b471a410dbf6859cd50f53ce9); salida de "Nivel de riesgo de la evaluadora" (YAML).</summary>
public enum NivelDeRiesgo
{
    /// <summary>bajo</summary>
    Bajo,
    /// <summary>medio</summary>
    Medio,
    /// <summary>alto</summary>
    Alto,
}
