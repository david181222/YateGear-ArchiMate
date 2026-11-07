// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Liberar el depósito" (SB-20, id-e2968b9d61094a948605f2615f69fff0).
namespace YateGear.CobrosYDeposito;

public sealed partial class LiberarElDepositoManejador
{
    // Reglas del "Contrato de servicio: Liberar el depósito" (id-d0043dfa6a2d42c9ad9162ffe81bff2b):
    //   Se rechaza si la inspección registró daños (REG-01). Se libera en máximo 3 días después de la
    //   devolución (resultado de la V1). Si la reserva se cancela, se libera al cancelar, sin inspección
    //   (V4-SUP-09).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(LiberarElDepositoDatos datos)
    {
        // REG-01, escrita a mano: con daños el depósito no se libera; se descuenta (SB-21).
        if (datos.Comando.ValorDeLosDanos is > 0m)
        {
            throw new ReglaIncumplida("REG-01", "La inspección registró daños: el depósito se descuenta, no se libera.");
        }
        // INT-PAG, escrita a mano: una orden sin confirmación de la pasarela no cuenta como hecha.
        if (!datos.CobrosPorLaPasarelaDePagos.Aprobada)
        {
            throw new ReglaIncumplida("INT-PAG", "La pasarela no aprobó la liberación del depósito.");
        }
    }

    // Escrito a mano: se libera el mismo día de la devolución o, si la reserva se canceló, el de la cancelación
    // (supuesto GEN-SUP-72); así se cumple "en máximo 3 días después de la devolución".
    private partial DateOnly FechaDeLaLiberacion(DateTime? horaDeRegreso, DateOnly? fechaDeLaCancelacion) =>
        horaDeRegreso is { } hora ? DateOnly.FromDateTime(hora)
            : fechaDeLaCancelacion ?? throw new DatoFaltante("hora de regreso o fecha de la cancelación");
}
