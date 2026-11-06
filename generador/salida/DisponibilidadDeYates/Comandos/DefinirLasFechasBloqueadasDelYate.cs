// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Definir las fechas bloqueadas del yate" (SB-03, id-f4ce9e396faf4c5395d097ec91278ec2).
namespace YateGear.DisponibilidadDeYates;

public sealed partial class DefinirLasFechasBloqueadasDelYateManejador
{
    // Reglas del "Contrato de servicio: Definir las fechas bloqueadas del yate" (id-33c845069c4641b9ad2e9d7585624b70):
    //   Se rechaza si quien hace el cambio no es el propietario del yate (E2E-02). Se rechaza el bloqueo de
    //   fechas que ya tienen una reserva confirmada (REG-02).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("REG-01", "motivo");
    partial void ValidarReglas(DefinirLasFechasBloqueadasDelYateDatos datos)
    {
        // REG-02, escrita a mano: no se bloquean fechas que ya tienen una reserva confirmada (fechas ocupadas).
        // E2E-02 (solo el propietario cambia sus fechas) no se revisa: la aplicación no autentica a quien llama
        // (supuesto GEN-SUP-46).
        var comando = datos.Comando;
        if (datos.Resultado == DefinirLasFechasBloqueadasDelYateResultado.FechasBloqueadas
            && datos.CalendarioDelYate.RangoDeFechas.Any(r => r.EstadoDeLaFecha == EstadoDeLaFecha.Ocupada
                                                              && r.Inicio <= comando.Fin && comando.Inicio <= r.Fin))
        {
            throw new ReglaIncumplida("REG-02", "Esas fechas ya tienen una reserva confirmada.");
        }
    }
}
