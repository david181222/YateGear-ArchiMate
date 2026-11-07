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
        // V1, escrita a mano: todo cargo del cierre va con evidencia (las actas y fotos de entrega e inspección).
        if (datos.Comando.Evidencia.Count == 0)
        {
            throw new ReglaIncumplida("V1", "Todo cobro va con evidencia: no llegaron las actas ni las fotos de la entrega y la inspección.");
        }
        // INT-PAG, escrita a mano: un cobro sin confirmación de la pasarela no cuenta como pagado.
        if (!datos.CobrosPorLaPasarelaDePagos1.Aprobada || datos.CobrosPorLaPasarelaDePagos2 is { Aprobada: false })
        {
            throw new ReglaIncumplida("INT-PAG", "La pasarela no aprobó un cargo del cierre.");
        }
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
