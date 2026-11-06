// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Calificar al cliente" (SB-29, id-bc9ac3247ce043cfbaf82400004826b8).
namespace YateGear.Calificaciones;

public sealed partial class CalificarAlClienteManejador
{
    // Reglas del "Contrato de servicio: Calificar al cliente" (id-f8d6e31e5be242919d71ef22e34a7824):
    //   Una calificación por cada parte y arriendo, al cerrar el arriendo (E2E-07); se rechaza si el
    //   arriendo no está cerrado o si el propietario ya calificó.
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("REG-01", "motivo");
    partial void ValidarReglas(CalificarAlClienteDatos datos)
    {
    }
}
