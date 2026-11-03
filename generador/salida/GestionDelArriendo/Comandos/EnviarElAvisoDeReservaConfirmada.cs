// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Enviar el aviso de reserva confirmada" (SB-31, id-57da84f53a9742cea51396bf297bf06d).
namespace YateGear.GestionDelArriendo;

public sealed partial class EnviarElAvisoDeReservaConfirmadaManejador
{
    // Reglas del "Contrato de servicio: Enviar el aviso de reserva confirmada" (id-e3e5284cecbe41648a8d588b31e44156):
    //   Se rechaza si la reserva no está confirmada: el aviso sale solo después de confirmar (H-07).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("REG-01", "motivo");
    partial void ValidarReglas(EnviarElAvisoDeReservaConfirmadaDatos datos)
    {
    }
}
