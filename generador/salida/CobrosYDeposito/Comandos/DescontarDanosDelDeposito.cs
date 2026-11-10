// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Descontar daños del depósito" (SB-21, id-53533cc505c540bbafcb8473107780c3).
namespace YateGear.CobrosYDeposito;

public sealed partial class DescontarDanosDelDepositoManejador
{
    // Reglas del "Contrato de servicio: Descontar daños del depósito" (id-31ee84a6c3c14f06908a6b41dce32745):
    //   Se rechaza un descuento sin evidencia (principio "Todo cobro va con evidencia", V1). Se hace en
    //   máximo 3 días después de la devolución (resultado de la V1). El valor de los daños llega con la
    //   inspección (V4-SUP-03).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(DescontarDanosDelDepositoDatos datos)
    {
        // V1, REG-01 e INT-PAG: declaradas en el YAML (reglas); la revisa el código generado antes de llamar aquí.
    }

    // Escrito a mano: H-10 y SB-21, se descuenta hasta el valor del depósito; lo que sobra se libera en la misma operación
    // y lo que excede el depósito se reclama a la aseguradora (SB-16).
    private partial decimal ValorDescontadoDelDeposito(decimal valorDeLosDanos, decimal valorDelDeposito) =>
        Math.Min(Math.Max(0m, valorDeLosDanos), valorDelDeposito);

    private partial decimal SaldoLiberado(decimal valorDeLosDanos, decimal valorDelDeposito) =>
        valorDelDeposito - ValorDescontadoDelDeposito(valorDeLosDanos, valorDelDeposito);

    private partial decimal ValorQueExcedeElDeposito(decimal valorDeLosDanos, decimal valorDelDeposito) =>
        Math.Max(0m, valorDeLosDanos - valorDelDeposito);
}
