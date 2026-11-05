// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Determinar las diferencias entre entrega y devolución" (SB-24, id-8222df5442934cf5a117ced88ec7329e).
namespace YateGear.OperacionDelArriendo;

public sealed partial class DeterminarLasDiferenciasEntreEntregaYDevolucionManejador
{
    // Reglas del "Contrato de servicio: Determinar las diferencias entre entrega y devolución" (id-970ca0e1b9194b2d8fc058310bb1fca9):
    //   Se rechaza si falta el acta de entrega o la de inspección, porque la comparación de las dos es la
    //   evidencia (H-13).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(DeterminarLasDiferenciasEntreEntregaYDevolucionDatos datos)
    {
    }

    // PENDIENTE: valor provisional de "combustible consumido" (decimal), dato calculado del evento "Diferencias determinadas".
    // Regla de la que sale: contrato SB-24, salida:
    //   Combustible consumido, horas adicionales y daños, con la evidencia de cada uno.
    // Escrito a mano: lo que bajó el nivel entre la entrega (tanque lleno, H-13) y la devolución; nunca negativo.
    private partial decimal CombustibleConsumido(DeterminarLasDiferenciasEntreEntregaYDevolucionDatos datos) =>
        Math.Max(0m, datos.ActaDeEntrega.NivelDeCombustible - datos.ActaDeInspeccion.NivelDeCombustible);

    // PENDIENTE: valor provisional de "horas adicionales" (decimal), dato calculado del evento "Diferencias determinadas".
    // Regla de la que sale: contrato SB-24, salida:
    //   Combustible consumido, horas adicionales y daños, con la evidencia de cada uno.
    // Escrito a mano: horas completas desde el fin acordado hasta el regreso; nunca negativas. El fin acordado es el
    // final del día de fin de la reserva confirmada (supuesto GEN-SUP-49).
    private partial decimal HorasAdicionales(DeterminarLasDiferenciasEntreEntregaYDevolucionDatos datos)
    {
        var finAcordado = datos.ReservaConfirmada.Fin.AddDays(1).ToDateTime(TimeOnly.MinValue);
        var horas = (datos.ActaDeInspeccion.HoraDeRegreso - finAcordado).TotalHours;
        return horas <= 0 ? 0m : (decimal)Math.Ceiling(horas);
    }

    // PENDIENTE: valor provisional de "valor de los daños" (decimal), dato calculado del evento "Diferencias determinadas".
    // Regla de la que sale: contrato SB-24, salida:
    //   Combustible consumido, horas adicionales y daños, con la evidencia de cada uno.
    // Escrito a mano: la suma de los daños encontrados, con el valor que trae la inspección (V4-SUP-03).
    private partial decimal ValorDeLosDanos(DeterminarLasDiferenciasEntreEntregaYDevolucionDatos datos) =>
        datos.ActaDeInspeccion.DanoEncontrado.Sum(d => d.Valor);
}
