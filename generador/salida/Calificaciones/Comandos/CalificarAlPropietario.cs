// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Calificar al propietario" (SB-28, id-b058bd36e7784e5ea81ab24c8dd3a4bb).
namespace YateGear.Calificaciones;

public sealed partial class CalificarAlPropietarioManejador
{
    // Reglas del "Contrato de servicio: Calificar al propietario" (id-c5fdbb67cdcb45b8a47cdc8a46a4f270):
    //   Una calificación por cada parte y arriendo, al cerrar el arriendo (E2E-07); se rechaza si el
    //   arriendo no está cerrado o si el cliente ya calificó.
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("REG-01", "motivo");
    partial void ValidarReglas(CalificarAlPropietarioDatos datos)
    {
    }
}
