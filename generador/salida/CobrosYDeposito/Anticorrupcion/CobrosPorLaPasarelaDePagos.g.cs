// Generado desde ArchiMate: ApplicationService "Cobros por la pasarela de pagos" (SA-06, id-1cdb2efd83d648a9bc004fe001343244).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada del servicio SA "Cobros por la pasarela de pagos" (SA-06).</summary>
public sealed record CobrosPorLaPasarelaDePagosEntrada(
    TipoDeOrden TipoDeOrden,
    string NumeroDelArriendo,
    decimal Valor,
    string? MedioDePago
);

/// <summary>Salida del servicio SA "Cobros por la pasarela de pagos" (SA-06).</summary>
public sealed record CobrosPorLaPasarelaDePagosSalida(
    bool Aprobada,
    string Comprobante,
    DateOnly? VencimientoDelBloqueo
);

/// <summary>Servicio de la capa anticorrupción "Cobros por la pasarela de pagos" (SA-06).</summary>
/// <remarks>
/// <para>Interfaz: "Interfaz con la pasarela de pagos" (id-219ca443aa4b4a7c8d2fc396e5bf3c9d).
/// Contraparte: ApplicationComponent "Sistema de la pasarela de pagos" (id-2f0cc96688e1475489c549d46f5860aa), sistema externo.</para>
/// <para>Flujos: entra "Aprobación o rechazo" (id-6681fd87a19e4b29a898c8f4a95d4294); sale "Órdenes de cobro y del depósito" (id-be5aa77b17854574a10415344197af5e).</para>
/// <para>Contrato de servicio: Cobros por la pasarela de pagos (id-1a2ba27625934f1c938f22171dc72916). Entrada: Tipo de orden, arriendo, valor y medio de pago.
/// Salida: Orden aprobada o rechazada, con su comprobante o código de autorización. Reglas: Una orden sin confirmación de la pasarela no cuenta como pago hecho (INT-PAG).</para>
/// </remarks>
public interface ICobrosPorLaPasarelaDePagos
{
    /// <summary>Llama al servicio.</summary>
    CobrosPorLaPasarelaDePagosSalida Llamar(CobrosPorLaPasarelaDePagosEntrada entrada);
}

/// <summary>"Sistema de la pasarela de pagos" simulado: responde con los valores fijos del YAML
/// (casos en orden y, si ninguno se cumple, respuesta_por_defecto).</summary>
public sealed class CobrosPorLaPasarelaDePagosSimulado(Bitacora bitacora) : ICobrosPorLaPasarelaDePagos
{
    /// <inheritdoc />
    public CobrosPorLaPasarelaDePagosSalida Llamar(CobrosPorLaPasarelaDePagosEntrada entrada)
    {
        var respuesta =
            (entrada.MedioDePago == "TARJETA-RECHAZADA") ? new CobrosPorLaPasarelaDePagosSalida(false, "RECHAZADA", null) :
            (entrada.TipoDeOrden == TipoDeOrden.BloqueoDelDeposito) ? new CobrosPorLaPasarelaDePagosSalida(true, "AUT-0001", new DateOnly(2026, 3, 29)) :
            (entrada.TipoDeOrden == TipoDeOrden.Alquiler) ? new CobrosPorLaPasarelaDePagosSalida(true, "PAG-ALQ-0001", null) :
            (entrada.TipoDeOrden == TipoDeOrden.Seguro) ? new CobrosPorLaPasarelaDePagosSalida(true, "PAG-SEG-0001", null) :
            (entrada.TipoDeOrden == TipoDeOrden.CombustibleConsumido) ? new CobrosPorLaPasarelaDePagosSalida(true, "PAG-COM-0001", null) :
            (entrada.TipoDeOrden == TipoDeOrden.TiempoAdicional) ? new CobrosPorLaPasarelaDePagosSalida(true, "PAG-TAD-0001", null) :
            (entrada.TipoDeOrden == TipoDeOrden.Reembolso) ? new CobrosPorLaPasarelaDePagosSalida(true, "REE-0001", null) :
            (entrada.TipoDeOrden == TipoDeOrden.LiberacionDelDeposito) ? new CobrosPorLaPasarelaDePagosSalida(true, "LIB-0001", null) :
            (entrada.TipoDeOrden == TipoDeOrden.DescuentoDelDeposito) ? new CobrosPorLaPasarelaDePagosSalida(true, "DES-0001", null) :
            new CobrosPorLaPasarelaDePagosSalida(true, "PAG-0001", null);
        bitacora.Anotar("llamada a servicio SA", "Cobros por la pasarela de pagos", new { entrada, respuesta });
        return respuesta;
    }
}
