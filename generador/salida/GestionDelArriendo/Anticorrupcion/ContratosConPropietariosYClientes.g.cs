// Generado desde ArchiMate: ApplicationService "Contratos con propietarios y clientes" (SA-02, id-18b80ed18f3d4d43a5290e01b90ca4eb).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada del servicio SA "Contratos con propietarios y clientes" (SA-02).</summary>
public sealed record ContratosConPropietariosYClientesEntrada(
    string NumeroDelArriendo
);

/// <summary>Salida del servicio SA "Contratos con propietarios y clientes" (SA-02).</summary>
public sealed record ContratosConPropietariosYClientesSalida(
    string ReferenciaDelContratoFirmado,
    EstadoDelContrato EstadoDelContrato,
    DateOnly? FechaDeFirma,
    string CondicionesDeCancelacion
);

/// <summary>Servicio de la capa anticorrupción "Contratos con propietarios y clientes" (SA-02).</summary>
/// <remarks>
/// <para>Interfaz: "Pantalla de registro de contratos" (id-a7b78492e6714137865f37c41eb78b19).
/// Contraparte: BusinessFunction "Gestión de contratos" (id-03be3f82b87240b1bbabf2bfd90332eb).</para>
/// <para>Flujos: entra "Contrato firmado" (id-92ca9accc62149968734d75dbc72b362); sale "Datos para el contrato" (id-bcd7145d93fb45e2b611264f8d602286).</para>
/// <para>Contrato de servicio: Contratos con propietarios y clientes (id-3f0f0a61815d4247bbb2d2cf80f1ad6e). Entrada: Datos del arriendo o del propietario para el contrato, o número de contrato a consultar.
/// Salida: Estado del contrato (enviado o firmado), fecha de firma, condiciones de cancelación y, si está firmado, la referencia del contrato firmado. Reglas: El contrato del cliente no se envía antes de que el riesgo salga aceptable (INT-CON).</para>
/// </remarks>
public interface IContratosConPropietariosYClientes
{
    /// <summary>Llama al servicio.</summary>
    ContratosConPropietariosYClientesSalida Llamar(ContratosConPropietariosYClientesEntrada entrada);
}

/// <summary>"Gestión de contratos" simulado: responde con los valores fijos del YAML
/// (casos en orden y, si ninguno se cumple, respuesta_por_defecto).</summary>
public sealed class ContratosConPropietariosYClientesSimulado(Bitacora bitacora) : IContratosConPropietariosYClientes
{
    /// <inheritdoc />
    public ContratosConPropietariosYClientesSalida Llamar(ContratosConPropietariosYClientesEntrada entrada)
    {
        var respuesta =
            new ContratosConPropietariosYClientesSalida("CON-0001", EstadoDelContrato.Firmado, new DateOnly(2026, 1, 10), "Condiciones de prueba");
        bitacora.Anotar("llamada a servicio SA", "Contratos con propietarios y clientes", new { entrada, respuesta });
        return respuesta;
    }
}
