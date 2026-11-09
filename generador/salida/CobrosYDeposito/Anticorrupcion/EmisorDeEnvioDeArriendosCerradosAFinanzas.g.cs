// Generado desde ArchiMate: ApplicationService "Envío de arriendos cerrados a Finanzas" (SA-08, id-415716c21d684fd5b6f0a59dab8bbc17).
// Capa anticorrupción, lo que sale (G11): lo que la aplicación envía por este servicio SA cuando ocurre un evento del
// contexto (envia del YAML). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Mensaje "Arriendo cerrado para Finanzas" que la aplicación envía por "Envío de arriendos cerrados a Finanzas" cuando ocurre "Cuenta del arriendo cerrada".</summary>
public sealed record ArriendoCerradoParaFinanzas(
    string NumeroDelArriendo,
    string Propietario,
    string IdentificadorDelYate,
    decimal ValorDelAlquiler,
    decimal Comision,
    decimal ValorDelPropietario
);

/// <summary>Lo que la aplicación envía a "Pagar mensualmente al propietario" por "Envío de arriendos cerrados a Finanzas" (SA-08). No espera respuesta
/// (lenguaje publicado).</summary>
/// <remarks>
/// <para>Interfaz: "Registro de arriendos cerrados para Finanzas" (id-3cfd84c427b943df83d5b8cfe5dee869).
/// Contraparte: BusinessProcess "Pagar mensualmente al propietario" (id-2436b7f69f814e539e5d62b6168b8f70).</para>
/// <para>Flujos: sale "Valores del arriendo cerrado" (id-dee064888f3f49b583a4383207f5b8a8).</para>
/// <para>Contrato de servicio: Envío de arriendos cerrados a Finanzas (id-4a7264e1a5af452bbc6909749a97c85d). Entrada: Cuentas cerradas del arriendo.
/// Salida: Registro recibido por el proceso de pago mensual al propietario. Reglas: sin reglas.</para>
/// </remarks>
public interface IEmisorDeEnvioDeArriendosCerradosAFinanzas
{
    /// <summary>Envía "Arriendo cerrado para Finanzas".</summary>
    void Enviar(ArriendoCerradoParaFinanzas mensaje);
}

/// <summary>"Pagar mensualmente al propietario" simulado: anota cada envío en la bitácora.</summary>
public sealed class EmisorDeEnvioDeArriendosCerradosAFinanzasSimulado(Bitacora bitacora) : IEmisorDeEnvioDeArriendosCerradosAFinanzas
{
    /// <inheritdoc />
    public void Enviar(ArriendoCerradoParaFinanzas mensaje) => bitacora.Anotar("envío por servicio SA", "Envío de arriendos cerrados a Finanzas: Arriendo cerrado para Finanzas", mensaje);
}
