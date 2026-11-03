// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Registrar el avance del arriendo" (SB-09, id-5be75381f2364a9cb9fa8d4247dce743).
namespace YateGear.GestionDelArriendo;

public sealed partial class RegistrarElAvanceDelArriendoManejador
{
    // Reglas del "Contrato de servicio: Registrar el avance del arriendo" (id-c6439672662d41ea93ee102abbe217eb):
    //   Se rechaza cerrar el arriendo antes de terminar los ajustes de dinero, porque con ellos se cierra
    //   (E2E-01).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("REG-01", "motivo");
    partial void ValidarReglas(RegistrarElAvanceDelArriendoDatos datos)
    {
    }
}
