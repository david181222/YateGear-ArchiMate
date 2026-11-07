// Generado desde ArchiMate: ApplicationComponent "Contexto Cobros y depósito" (id-859686865fd4465397859188d62c971c).
// Enums del contexto, de los campos del modelo y del YAML. No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Enum "Concepto del cobro". Se usa en: campo "concepto" de "Cobro" (id-73b07f4ddacf4826ad340226a0e59119).</summary>
public enum ConceptoDelCobro
{
    /// <summary>alquiler</summary>
    Alquiler,
    /// <summary>seguro</summary>
    Seguro,
    /// <summary>combustible consumido</summary>
    CombustibleConsumido,
    /// <summary>tiempo adicional</summary>
    TiempoAdicional,
    /// <summary>reembolso</summary>
    Reembolso,
}

/// <summary>Enum "Decisión sobre el depósito". Se usa en: entrada de "Cerrar las cuentas del arriendo" (YAML).</summary>
public enum DecisionSobreElDeposito
{
    /// <summary>liberado</summary>
    Liberado,
    /// <summary>descontado</summary>
    Descontado,
}

/// <summary>Enum "Estado de la cuenta". Se usa en: estado de la raíz "Cuenta del arriendo" (YAML); salida de "Consultar el estado de cuenta del arriendo" (YAML).</summary>
public enum EstadoDeLaCuenta
{
    /// <summary>abierta</summary>
    Abierta,
    /// <summary>cerrada</summary>
    Cerrada,
}

/// <summary>Enum "Estado del depósito". Se usa en: estado de la raíz "Depósito para daños" (YAML); calculados de "Consultar el estado de cuenta del arriendo" (YAML).</summary>
public enum EstadoDelDeposito
{
    /// <summary>bloqueado</summary>
    Bloqueado,
    /// <summary>liberado</summary>
    Liberado,
    /// <summary>descontado</summary>
    Descontado,
}

/// <summary>Enum "Estado del reclamo". Se usa en: estado de la raíz "Reclamo a la aseguradora" (YAML).</summary>
public enum EstadoDelReclamo
{
    /// <summary>enviado</summary>
    Enviado,
}

/// <summary>Enum "Estado del reclamo en la aseguradora". Se usa en: salida de "Pólizas y reclamos de la aseguradora" (YAML); datos del evento "Reclamo enviado a la aseguradora" (YAML).</summary>
public enum EstadoDelReclamoEnLaAseguradora
{
    /// <summary>recibido</summary>
    Recibido,
    /// <summary>rechazado</summary>
    Rechazado,
}

/// <summary>Enum "Solicitud a la aseguradora". Se usa en: entrada de "Pólizas y reclamos de la aseguradora" (YAML).</summary>
public enum SolicitudALaAseguradora
{
    /// <summary>póliza</summary>
    Poliza,
    /// <summary>reclamo</summary>
    Reclamo,
}

/// <summary>Enum "Tipo de orden". Se usa en: entrada de "Cobros por la pasarela de pagos" (YAML).</summary>
public enum TipoDeOrden
{
    /// <summary>alquiler</summary>
    Alquiler,
    /// <summary>seguro</summary>
    Seguro,
    /// <summary>combustible consumido</summary>
    CombustibleConsumido,
    /// <summary>tiempo adicional</summary>
    TiempoAdicional,
    /// <summary>reembolso</summary>
    Reembolso,
    /// <summary>bloqueo del depósito</summary>
    BloqueoDelDeposito,
    /// <summary>liberación del depósito</summary>
    LiberacionDelDeposito,
    /// <summary>descuento del depósito</summary>
    DescuentoDelDeposito,
}
