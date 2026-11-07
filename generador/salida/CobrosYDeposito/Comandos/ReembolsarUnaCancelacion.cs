// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Reembolsar una cancelación" (SB-15, id-599456d5ca8f45b0b82efa9a05b254d2).
namespace YateGear.CobrosYDeposito;

public sealed partial class ReembolsarUnaCancelacionManejador
{
    // Reglas del "Contrato de servicio: Reembolsar una cancelación" (id-3e6363728e104f31a5d3a2104e66869c):
    //   No se reembolsa la cancelación hecha muy cerca de la fecha; el plazo lo fija el contrato con el
    //   cliente (EXC-02, D-03).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(ReembolsarUnaCancelacionDatos datos)
    {
        // INT-PAG, escrita a mano: un reembolso sin confirmación de la pasarela no cuenta como hecho.
        if (datos.CobrosPorLaPasarelaDePagos is { Aprobada: false })
        {
            throw new ReglaIncumplida("INT-PAG", "La pasarela no aprobó el reembolso.");
        }
    }

    // Escrito a mano: se devuelve lo cobrado por el alquiler; el seguro no, porque la póliza ya se emitió
    // (supuesto GEN-SUP-70).
    private partial decimal ValorDelReembolso(CuentaDelArriendo cuentaDelArriendo) =>
        cuentaDelArriendo.Cobro.Where(c => c.Concepto == ConceptoDelCobro.Alquiler).Sum(c => c.Valor);

    // Escrito a mano: EXC-02 y D-03, se reembolsa si se canceló con los días de anticipación que pide el contrato.
    private partial bool Reembolsable(int diasDeAnticipacion, int diasMinimosParaElReembolso) =>
        diasDeAnticipacion >= diasMinimosParaElReembolso;
}
