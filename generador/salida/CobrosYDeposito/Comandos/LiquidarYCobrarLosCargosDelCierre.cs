// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Liquidar y cobrar los cargos del cierre" (SB-14, id-3101c7184ff44fbfb862a7645b4e6135).
namespace YateGear.CobrosYDeposito;

public sealed partial class LiquidarYCobrarLosCargosDelCierreManejador
{
    // Tarifas de prueba (supuesto GEN-SUP-68): el valor de cada punto del nivel de combustible y de cada hora adicional.
    private const decimal ValorPorPuntoDeCombustible = 10m;
    private const decimal ValorPorHoraAdicional = 50m;

    // Reglas del "Contrato de servicio: Liquidar y cobrar los cargos del cierre" (id-b7171db9da564944bab35b3666ab3c83):
    //   Se rechaza un cargo sin evidencia (principio "Todo cobro va con evidencia", V1). El combustible
    //   consumido siempre lo paga el cliente (REG-01).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(LiquidarYCobrarLosCargosDelCierreDatos datos)
    {
        // V1 e INT-PAG: declaradas en el YAML (reglas); la revisa el código generado antes de llamar aquí.
    }

    // Escrito a mano: REG-01, el combustible consumido siempre lo paga el cliente; nunca negativo.
    private partial decimal ValorDelCombustible(decimal combustibleConsumido) =>
        Math.Max(0m, combustibleConsumido) * ValorPorPuntoDeCombustible;

    // Escrito a mano: las horas adicionales por la tarifa de la hora; nunca negativo.
    private partial decimal ValorDelTiempoAdicional(decimal horasAdicionales) =>
        Math.Max(0m, horasAdicionales) * ValorPorHoraAdicional;

    // Escrito a mano: H-14, el tiempo adicional se cobra solo si el yate se devolvió tarde.
    private partial bool HayTiempoAdicional(decimal horasAdicionales) => horasAdicionales > 0m;
}
