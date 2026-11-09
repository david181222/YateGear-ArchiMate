// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationService "Consultar el estado de cuenta del arriendo" (SB-18, id-e093f7b040c243449523e515011813d0).
namespace YateGear.CobrosYDeposito;

public sealed partial class ConsultarElEstadoDeCuentaDelArriendoManejador
{
    // Reglas del "Contrato de servicio: Consultar el estado de cuenta del arriendo" (id-351bf3719c344a159d64e004c3eab7df):
    //   Se rechaza si quien consulta no es el cliente del arriendo ni un empleado de YateGear, porque son
    //   datos de pago (Ley 1581, H-19).
    //
    // No se revisa: la aplicación no autentica a quien llama (supuesto GEN-SUP-79, como GEN-SUP-46).
    partial void ValidarReglas(ConsultarElEstadoDeCuentaDelArriendoDatos datos)
    {
    }

    // Escrito a mano: los movimientos de la cuenta, en el orden en que se cobraron, con su concepto, valor y evidencia.
    // Sin fecha: el Cobro no la tiene (discrepancia 12).
    private partial List<Cobro> Movimientos(ConsultarElEstadoDeCuentaDelArriendoDatos datos) => datos.CuentaDelArriendo.Cobro.ToList();

    // Escrito a mano: el estado del depósito, si se bloqueó.
    private partial EstadoDelDeposito? EstadoDelDeposito(ConsultarElEstadoDeCuentaDelArriendoDatos datos) =>
        datos.DepositoParaDanos?.Estado;
}
