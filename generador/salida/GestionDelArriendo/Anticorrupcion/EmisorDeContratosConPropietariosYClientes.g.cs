// Generado desde ArchiMate: ApplicationService "Contratos con propietarios y clientes" (SA-02, id-18b80ed18f3d4d43a5290e01b90ca4eb).
// Capa anticorrupción, lo que sale (G11): lo que YateGear envía por este servicio SA cuando ocurre un evento del
// contexto (envia del YAML). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Mensaje "Datos para el contrato del cliente" que YateGear envía por "Contratos con propietarios y clientes" cuando ocurre "Riesgo aceptable obtenido".</summary>
public sealed record DatosParaElContratoDelCliente(
    string NumeroDelArriendo,
    string ReferenciaAlCRM,
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin,
    decimal PrecioPorDia
);

/// <summary>Lo que YateGear envía a "Gestión de contratos" por "Contratos con propietarios y clientes" (SA-02). No espera respuesta
/// (lenguaje publicado).</summary>
/// <remarks>
/// <para>Interfaz: "Pantalla de registro de contratos" (id-a7b78492e6714137865f37c41eb78b19).
/// Contraparte: BusinessFunction "Gestión de contratos" (id-03be3f82b87240b1bbabf2bfd90332eb).</para>
/// <para>Flujos: entra "Contrato firmado" (id-92ca9accc62149968734d75dbc72b362); sale "Datos para el contrato" (id-bcd7145d93fb45e2b611264f8d602286).</para>
/// <para>Contrato de servicio: Contratos con propietarios y clientes (id-3f0f0a61815d4247bbb2d2cf80f1ad6e). Entrada: Datos del arriendo o del propietario para el contrato, o número de contrato a consultar.
/// Salida: Estado del contrato (enviado o firmado), fecha de firma, condiciones de cancelación y, si está firmado, la referencia del contrato firmado. Reglas: El contrato del cliente no se envía antes de que el riesgo salga aceptable (INT-CON).</para>
/// </remarks>
public interface IEmisorDeContratosConPropietariosYClientes
{
    /// <summary>Envía "Datos para el contrato del cliente".</summary>
    void Enviar(DatosParaElContratoDelCliente mensaje);
}

/// <summary>"Gestión de contratos" simulado: anota cada envío en la bitácora.</summary>
public sealed class EmisorDeContratosConPropietariosYClientesSimulado(Bitacora bitacora) : IEmisorDeContratosConPropietariosYClientes
{
    /// <inheritdoc />
    public void Enviar(DatosParaElContratoDelCliente mensaje) => bitacora.Anotar("envío por servicio SA", "Contratos con propietarios y clientes: Datos para el contrato del cliente", mensaje);
}
