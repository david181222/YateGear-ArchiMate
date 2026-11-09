// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Cerrar las cuentas del arriendo" (SB-17, id-5ef920b9e381405495dbdfe1877eb75b).
namespace YateGear.CobrosYDeposito;

public sealed partial class CerrarLasCuentasDelArriendoManejador
{
    // Comisión de YateGear sobre el alquiler (supuesto GEN-SUP-74: valor de prueba; la fija el contrato con el propietario).
    private const decimal PorcentajeDeComision = 0.20m;

    // Reglas del "Contrato de servicio: Cerrar las cuentas del arriendo" (id-4cf062b2782044669f3d49e65f16d93b):
    //   Se rechaza mientras falte un cargo del cierre o la decisión sobre el depósito, porque con los
    //   ajustes se cierra el arriendo (E2E-01).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(CerrarLasCuentasDelArriendoDatos datos)
    {
        // E2E-01, escrita a mano. El cargo del cierre que nunca falta es el combustible consumido (REG-01); la decisión
        // sobre el depósito la trae la política (uno_de) o quien llama. Por la política, las dos ya llegaron (D7).
        if (!datos.CuentaDelArriendo.Cobro.Any(c => c.Concepto == ConceptoDelCobro.CombustibleConsumido))
        {
            throw new ReglaIncumplida("E2E-01", "Falta un cargo del cierre: el combustible consumido.");
        }
        if (datos.Comando.DecisionSobreElDeposito is null)
        {
            throw new ReglaIncumplida("E2E-01", "Falta la decisión sobre el depósito.");
        }
    }

    // Escrito a mano: lo cobrado por el alquiler (H-11).
    private partial decimal ValorDelAlquiler(CuentaDelArriendo cuentaDelArriendo) =>
        cuentaDelArriendo.Cobro.Where(c => c.Concepto == ConceptoDelCobro.Alquiler).Sum(c => c.Valor);

    // Escrito a mano: H-11 y CTX-01, YateGear se queda con su comisión y el resto es del propietario.
    private partial decimal Comision(decimal valorDelAlquiler) => decimal.Round(valorDelAlquiler * PorcentajeDeComision, 2);

    private partial decimal ValorDelPropietario(decimal valorDelAlquiler, decimal comision) => valorDelAlquiler - comision;
}
