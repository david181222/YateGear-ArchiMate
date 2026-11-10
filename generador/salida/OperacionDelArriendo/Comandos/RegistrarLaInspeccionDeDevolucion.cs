// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Registrar la inspección de devolución" (SB-23, id-c6f7cd3f402f41feb9d986570982815a).
namespace YateGear.OperacionDelArriendo;

public sealed partial class RegistrarLaInspeccionDeDevolucionManejador
{
    // Reglas del "Contrato de servicio: Registrar la inspección de devolución" (id-6c8c966e7a6248108baa667653bba6bb):
    //   Se rechaza una inspección sin fotos (H-13). El valor de los daños llega con la inspección
    //   (V4-SUP-03).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(RegistrarLaInspeccionDeDevolucionDatos datos)
    {
        // H-13: declarada en el YAML (reglas); la revisa el código generado antes de llamar aquí.
    }
}
