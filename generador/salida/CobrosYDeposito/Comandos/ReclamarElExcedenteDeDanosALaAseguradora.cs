// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Reclamar el excedente de daños a la aseguradora" (SB-16, id-afb038030e754dd490f69fcbf6a446e0).
namespace YateGear.CobrosYDeposito;

public sealed partial class ReclamarElExcedenteDeDanosALaAseguradoraManejador
{
    // Reglas del "Contrato de servicio: Reclamar el excedente de daños a la aseguradora" (id-68d91d580faf4234a20279768c8520e6):
    //   Se rechaza si el daño no supera el depósito (REG-01) o si falta la evidencia de la entrega y de la
    //   inspección (EXC-02).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(ReclamarElExcedenteDeDanosALaAseguradoraDatos datos)
    {
        // REG-01, escrita a mano: solo se reclama lo que el daño supera el depósito. La política tampoco dispara el
        // comando en ese caso (salvo, en el YAML); la regla cubre la llamada directa.
        if (datos.Comando.ValorQueExcedeElDeposito <= 0m)
        {
            throw new ReglaIncumplida("REG-01", "El daño no supera el depósito: no hay nada que reclamar a la aseguradora.");
        }
        // EXC-02, escrita a mano: el reclamo va con la evidencia de la entrega y de la inspección.
        if (datos.Comando.Evidencia.Count == 0)
        {
            throw new ReglaIncumplida("EXC-02", "Falta la evidencia de la entrega y de la inspección.");
        }
    }

    // Escrito a mano: el número de la póliza que emitió la aseguradora al reservar, que guarda la cuenta (discrepancia 11).
    private partial string NumeroDePoliza(CuentaDelArriendo cuentaDelArriendo) =>
        cuentaDelArriendo.PolizaDelArriendo?.Numero ?? throw new DatoFaltante("número de póliza");
}
