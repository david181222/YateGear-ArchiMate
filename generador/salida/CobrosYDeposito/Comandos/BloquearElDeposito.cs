// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Bloquear el depósito" (SB-19, id-43d3a21049834a9ea5e2f3f8b3079d0a).
using System.Globalization;

namespace YateGear.CobrosYDeposito;

public sealed partial class BloquearElDepositoManejador
{
    // Reglas del "Contrato de servicio: Bloquear el depósito" (id-be586e0ecad5498c8973ace01690688c):
    //   Se rechaza si el bloqueo vencería antes del cierre: la autorización en tarjeta de crédito dura 28
    //   días (V4-SUP-07, contraste de H-10). En la práctica, la fecha de fin del arriendo no puede pasar de
    //   unos 25 días después de reservar.
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(BloquearElDepositoDatos datos)
    {
        // INT-PAG: declarada en el YAML (reglas); la revisa el código generado antes de llamar aquí.
        // V4-SUP-07, escrita a mano: el depósito se libera o se descuenta hasta 3 días después de la devolución
        // (resultado de la V1), así que el bloqueo no puede vencer antes de esa fecha.
        var pasarela = datos.CobrosPorLaPasarelaDePagos;
        var cierre = datos.Comando.Fin.AddDays(3);
        if (pasarela.VencimientoDelBloqueo is not { } vence || vence < cierre)
        {
            throw new ReglaIncumplida("V4-SUP-07",
                $"El bloqueo vence el {Fecha(pasarela.VencimientoDelBloqueo)} y el cierre puede llegar hasta el {Fecha(cierre)}.");
        }
    }

    private static string Fecha(DateOnly? fecha) =>
        fecha?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) ?? "(sin fecha)";
}
