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
        // REG-01 e INT-PAG: declaradas en el YAML (reglas); la revisa el código generado antes de llamar aquí.
    }

    // Escrito a mano: se libera el mismo día de la devolución o, si la reserva se canceló, el de la cancelación
    // (supuesto GEN-SUP-72); así se cumple "en máximo 3 días después de la devolución".
    private partial DateOnly FechaDeLaLiberacion(DateTime? horaDeRegreso, DateOnly? fechaDeLaCancelacion) =>
        horaDeRegreso is { } hora ? DateOnly.FromDateTime(hora)
            : fechaDeLaCancelacion ?? throw new DatoFaltante("hora de regreso o fecha de la cancelación");
}
