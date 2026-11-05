// Generado desde ArchiMate: ApplicationComponent "Contexto Disponibilidad de yates" (id-0d93d731f6fd4b21acbf20d3cb28cf6f).
// Enums del contexto, de los campos del modelo y del YAML. No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Enum "Acción sobre el bloqueo". Se usa en: entrada de "Definir las fechas bloqueadas del yate" (YAML).</summary>
public enum AccionSobreElBloqueo
{
    /// <summary>bloquear</summary>
    Bloquear,
    /// <summary>desbloquear</summary>
    Desbloquear,
}

/// <summary>Enum "Acción sobre la ocupación". Se usa en: entrada de "Gestionar la ocupación del calendario" (YAML).</summary>
public enum AccionSobreLaOcupacion
{
    /// <summary>apartar</summary>
    Apartar,
    /// <summary>ocupar</summary>
    Ocupar,
    /// <summary>soltar</summary>
    Soltar,
}

/// <summary>Enum "Estado de la fecha". Se usa en: campo "estado de la fecha" de "Rango de fechas" (id-ada4b300178d4ff6a7a01bc9405f74fb).</summary>
public enum EstadoDeLaFecha
{
    /// <summary>bloqueada</summary>
    Bloqueada,
    /// <summary>apartada</summary>
    Apartada,
    /// <summary>ocupada</summary>
    Ocupada,
}

/// <summary>Enum "Estado del calendario". Se usa en: estado de la raíz "Calendario del yate" (YAML).</summary>
public enum EstadoDelCalendario
{
    /// <summary>activo</summary>
    Activo,
}

/// <summary>Enum "Estado del contrato". Se usa en: salida de "Contratos con propietarios y clientes" (YAML).</summary>
public enum EstadoDelContrato
{
    /// <summary>enviado</summary>
    Enviado,
    /// <summary>firmado</summary>
    Firmado,
}

/// <summary>Enum "Estado del yate". Se usa en: estado de la raíz "Yate" (YAML).</summary>
public enum EstadoDelYate
{
    /// <summary>registrado</summary>
    Registrado,
}
