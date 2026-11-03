// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Confirmar la reserva" (SB-07, id-b5e59d3c453a410580107b2287cd76d2).
namespace YateGear.GestionDelArriendo;

public sealed partial class ConfirmarLaReservaManejador
{
    // Reglas del "Contrato de servicio: Confirmar la reserva" (id-684d5b92ffbb4fefa001d8936128713c):
    //   No se confirma sin riesgo aceptable, contrato firmado y pagos completos (REG-01); si falta uno, se
    //   rechaza indicando cuál.
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("REG-01", "motivo");
    partial void ValidarReglas(ConfirmarLaReservaDatos datos)
    {
        // REG-01, escrita a mano: si falta algo, se rechaza indicando qué.
        var faltan = new List<string>();
        var riesgo = datos.Arriendo.EvaluacionDeRiesgo;
        if (riesgo is null || riesgo.Nivel == NivelDeRiesgo.Alto)          // aceptable es bajo o medio (V4-SUP-02)
        {
            faltan.Add("riesgo aceptable");
        }
        if (datos.ContratosConPropietariosYClientes.EstadoDelContrato != EstadoDelContrato.Firmado)
        {
            faltan.Add("contrato firmado");
        }
        var comando = datos.Comando;
        if (string.IsNullOrWhiteSpace(comando.ComprobanteDelAlquiler)
            || string.IsNullOrWhiteSpace(comando.ComprobanteDelSeguro)
            || string.IsNullOrWhiteSpace(comando.AutorizacionDelBloqueoDelDeposito))
        {
            faltan.Add("pagos completos");
        }
        if (faltan.Count > 0)
        {
            throw new ReglaIncumplida("REG-01", "No se confirma sin " + string.Join(", ", faltan) + ".");
        }
    }
}
