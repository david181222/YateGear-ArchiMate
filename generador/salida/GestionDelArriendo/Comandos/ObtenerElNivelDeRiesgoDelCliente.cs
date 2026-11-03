// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Obtener el nivel de riesgo del cliente" (SB-12, id-2a55b3149f0d4388ba3551743aa65cf4).
namespace YateGear.GestionDelArriendo;

public sealed partial class ObtenerElNivelDeRiesgoDelClienteManejador
{
    // Reglas del "Contrato de servicio: Obtener el nivel de riesgo del cliente" (id-3f0507fda0fa42ecb67a0f2e7864f30e):
    //   Con riesgo alto el arriendo no se realiza (REG-01); aceptable es bajo o medio (V4-SUP-02). No se
    //   envían datos a la evaluadora sin la autorización del cliente (H-19).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("REG-01", "motivo");
    partial void ValidarReglas(ObtenerElNivelDeRiesgoDelClienteDatos datos)
    {
    }
}
