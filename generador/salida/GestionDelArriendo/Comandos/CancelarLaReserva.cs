// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Cancelar la reserva" (SB-08, id-ea0f1874f954489589820b4aa2761e3f).
namespace YateGear.GestionDelArriendo;

public sealed partial class CancelarLaReservaManejador
{
    // Reglas del "Contrato de servicio: Cancelar la reserva" (id-1b76f672e55f4171bc42f6e9e3700c3a):
    //   Se rechaza si el arriendo ya empezó: la cancelación es antes de la fecha del arriendo (EXC-02). La
    //   anticipación que da derecho a reembolso está en el contrato con el cliente (D-03).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("REG-01", "motivo");
    partial void ValidarReglas(CancelarLaReservaDatos datos)
    {
    }

    // PENDIENTE: valor provisional de "días de anticipación" (int), dato calculado del evento "Reserva cancelada".
    // Regla de la que sale: contrato SB-08, salida:
    //   Arriendo cancelado y días de anticipación frente a la fecha de inicio.
    private partial int DiasDeAnticipacion(CancelarLaReservaDatos datos) => 0;
}
