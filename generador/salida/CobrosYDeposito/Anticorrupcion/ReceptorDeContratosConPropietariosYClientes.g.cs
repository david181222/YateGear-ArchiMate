// Generado desde ArchiMate: ApplicationService "Contratos con propietarios y clientes" (SA-02, id-18b80ed18f3d4d43a5290e01b90ca4eb).
// Capa anticorrupción, lo que entra (G7): lo que el sistema externo le envía a YateGear por este servicio SA
// (recibe del YAML). No editar: el generador reescribe este archivo.
#nullable enable
using System.Text.Json;

namespace YateGear.CobrosYDeposito;

/// <summary>Mensaje "Contrato del cliente firmado" que "Contratos con propietarios y clientes" recibe del sistema externo. Dispara "Bloquear el depósito", "Cobrar alquiler y seguro".</summary>
public sealed record ContratoDelClienteFirmado(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    string Propietario,
    string ReferenciaAlCRM,
    DateOnly Inicio,
    DateOnly Fin,
    int Dias,
    decimal PrecioPorDia,
    decimal ValorDelSeguro,
    decimal ValorDelDeposito,
    string MedioDePago
);

/// <summary>Recibe lo que "Gestión de contratos" le envía a YateGear por "Contratos con propietarios y clientes" (SA-02)
/// y dispara el comando de cada mensaje, con sus datos por nombre.</summary>
/// <remarks>
/// <para>Contrato de servicio: Contratos con propietarios y clientes (id-3f0f0a61815d4247bbb2d2cf80f1ad6e). Entrada: Datos del arriendo o del propietario para el contrato, o número de contrato a consultar.</para>
/// <para>Interfaz "Pantalla de registro de contratos" (id-a7b78492e6714137865f37c41eb78b19).</para>
/// </remarks>
public sealed class ReceptorDeContratosConPropietariosYClientes(
    Bitacora bitacora,
    BloquearElDepositoManejador bloquearElDeposito,
    CobrarAlquilerYSeguroManejador cobrarAlquilerYSeguro
)
{
    /// <summary>Lee "Contrato del cliente firmado" desde JSON (si falta un dato obligatorio, DatoFaltante: 422) y dispara, en orden,
    /// "Bloquear el depósito", "Cobrar alquiler y seguro". Si uno falla, los siguientes no corren.</summary>
    public RespuestaDeComando RecibirContratoDelClienteFirmado(JsonElement json)
    {
        var mensaje = LectorDeEventos.Leer<ContratoDelClienteFirmado>(json, ("numeroDelArriendo", "número del arriendo"), ("identificadorDelYate", "identificador del yate"), ("propietario", "propietario"), ("referenciaAlCRM", "referencia al CRM"), ("inicio", "inicio"), ("fin", "fin"), ("dias", "días"), ("precioPorDia", "precio por día"), ("valorDelSeguro", "valor del seguro"), ("valorDelDeposito", "valor del depósito"), ("medioDePago", "medio de pago"));
        bitacora.Anotar("mensaje recibido", "Contratos con propietarios y clientes: Contrato del cliente firmado", mensaje);
        var respuestas = new List<RespuestaDeComando>();
        respuestas.Add(bloquearElDeposito.Manejar(new BloquearElDeposito(mensaje.NumeroDelArriendo, mensaje.ValorDelDeposito, mensaje.MedioDePago, mensaje.Fin)));
        respuestas.Add(cobrarAlquilerYSeguro.Manejar(new CobrarAlquilerYSeguro(mensaje.NumeroDelArriendo, mensaje.IdentificadorDelYate, mensaje.Propietario, mensaje.ReferenciaAlCRM, mensaje.Inicio, mensaje.Fin, mensaje.Dias, mensaje.PrecioPorDia, mensaje.ValorDelSeguro, mensaje.MedioDePago)));
        return RespuestaDeComando.Juntar("", respuestas);
    }
}
