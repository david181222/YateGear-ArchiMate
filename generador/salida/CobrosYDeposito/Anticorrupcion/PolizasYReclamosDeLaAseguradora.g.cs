// Generado desde ArchiMate: ApplicationService "Pólizas y reclamos de la aseguradora" (SA-03, id-45d9e0e4f7624937a6dfef70e2c3240a).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada del servicio SA "Pólizas y reclamos de la aseguradora" (SA-03).</summary>
public sealed record PolizasYReclamosDeLaAseguradoraEntrada(
    SolicitudALaAseguradora Solicitud,
    string NumeroDelArriendo,
    string? IdentificadorDelYate,
    string? ReferenciaAlCRM,
    DateOnly? Inicio,
    DateOnly? Fin,
    string? NumeroDePoliza,
    decimal? ValorDeLosDanos,
    decimal? ValorDescontadoDelDeposito,
    List<string>? Evidencia
);

/// <summary>Salida del servicio SA "Pólizas y reclamos de la aseguradora" (SA-03).</summary>
public sealed record PolizasYReclamosDeLaAseguradoraSalida(
    string Numero,
    decimal? Valor,
    EstadoDelReclamoEnLaAseguradora? EstadoDelReclamo
);

/// <summary>Servicio de la capa anticorrupción "Pólizas y reclamos de la aseguradora" (SA-03).</summary>
/// <remarks>
/// <para>Interfaz: "Interfaz con la aseguradora" (id-962979e809b243f3af41beef0f35a1b5).
/// Contraparte: ApplicationComponent "Sistema de la aseguradora" (id-d2840298523842f48f2d31491dbd7834), sistema externo.</para>
/// <para>Flujos: sale "Datos del arriendo; reclamo con evidencia" (id-877b1716069f4809a6f4f3bd499fe3e3); entra "Póliza; respuesta al reclamo" (id-6e6bcaca93734a8f8b4b0d62c5e3a172).</para>
/// <para>Contrato de servicio: Pólizas y reclamos de la aseguradora (id-351bb447422d45dc8f8144e4694621d0). Entrada: Datos del arriendo, o datos del reclamo con su evidencia.
/// Salida: Número y valor de la póliza, o número y estado del reclamo. Reglas: No se envía un reclamo si el daño no supera el depósito (INT-ASE).</para>
/// </remarks>
public interface IPolizasYReclamosDeLaAseguradora
{
    /// <summary>Llama al servicio.</summary>
    PolizasYReclamosDeLaAseguradoraSalida Llamar(PolizasYReclamosDeLaAseguradoraEntrada entrada);
}

/// <summary>"Sistema de la aseguradora" simulado: responde con los valores fijos del YAML
/// (casos en orden y, si ninguno se cumple, respuesta_por_defecto).</summary>
public sealed class PolizasYReclamosDeLaAseguradoraSimulado(Bitacora bitacora) : IPolizasYReclamosDeLaAseguradora
{
    /// <inheritdoc />
    public PolizasYReclamosDeLaAseguradoraSalida Llamar(PolizasYReclamosDeLaAseguradoraEntrada entrada)
    {
        var respuesta =
            (entrada.Solicitud == SolicitudALaAseguradora.Reclamo) ? new PolizasYReclamosDeLaAseguradoraSalida("SIN-0001", null, EstadoDelReclamoEnLaAseguradora.Recibido) :
            new PolizasYReclamosDeLaAseguradoraSalida("POL-0001", 120m, null);
        bitacora.Anotar("llamada a servicio SA", "Pólizas y reclamos de la aseguradora", new { entrada, respuesta });
        return respuesta;
    }
}
