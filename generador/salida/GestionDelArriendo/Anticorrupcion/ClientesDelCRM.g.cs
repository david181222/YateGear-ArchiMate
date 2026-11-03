// Generado desde ArchiMate: ApplicationService "Clientes del CRM" (SA-01, id-2a8748ebcb2c44bda5267072d3cd6c3c).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada del servicio SA "Clientes del CRM" (SA-01).</summary>
public sealed record ClientesDelCRMEntrada(
    string Cliente,
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin
);

/// <summary>Salida del servicio SA "Clientes del CRM" (SA-01).</summary>
public sealed record ClientesDelCRMSalida(
    string ReferenciaAlCRM
);

/// <summary>Servicio de la capa anticorrupción "Clientes del CRM" (SA-01).</summary>
/// <remarks>
/// <para>Interfaz: "Interfaz con el CRM" (id-50762e19dd0a427ca2544391c5ab5962).
/// Contraparte: ApplicationComponent "CRM" (id-caf28817537c4ca4bd1558fc179f647c), sistema externo.</para>
/// <para>Flujos: sale "Cliente y solicitud" (id-3802e0a5e3c948e294d1cbc90dd9270a); entra "Datos del cliente" (id-0581a80e8807487e9ef45514d306561f).</para>
/// <para>Contrato de servicio: Clientes del CRM (id-9c284e04c8ad4e1092a005b88ac34d5a). Entrada: Identificación del cliente, o datos del cliente y de su solicitud.
/// Salida: Datos del cliente con su referencia en el CRM, o confirmación del registro. Reglas: sin reglas.</para>
/// </remarks>
public interface IClientesDelCRM
{
    /// <summary>Llama al servicio.</summary>
    ClientesDelCRMSalida Llamar(ClientesDelCRMEntrada entrada);
}

/// <summary>"CRM" simulado: responde con los valores fijos del YAML
/// (casos en orden y, si ninguno se cumple, respuesta_por_defecto).</summary>
public sealed class ClientesDelCRMSimulado(Bitacora bitacora) : IClientesDelCRM
{
    /// <inheritdoc />
    public ClientesDelCRMSalida Llamar(ClientesDelCRMEntrada entrada)
    {
        var respuesta =
            (entrada.Cliente == "CLI-RIESGO-ALTO") ? new ClientesDelCRMSalida("CRM-0002") :
            new ClientesDelCRMSalida("CRM-0001");
        bitacora.Anotar("llamada a servicio SA", "Clientes del CRM", new { entrada, respuesta });
        return respuesta;
    }
}
