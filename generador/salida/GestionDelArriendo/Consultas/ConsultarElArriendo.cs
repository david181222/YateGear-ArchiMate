// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationService "Consultar el arriendo" (SB-10, id-ed6830eac52c4d5aa7983fb1edd63869).
namespace YateGear.GestionDelArriendo;

public sealed partial class ConsultarElArriendoManejador
{
    // Reglas del "Contrato de servicio: Consultar el arriendo" (id-cd8962c3c6d44cfb927557b1a4e45e53):
    //   Se rechaza si quien consulta no participa en el arriendo, porque son datos personales del cliente
    //   (Ley 1581, H-19).
    //
    // Para rechazar la consulta:
    //   throw new ReglaIncumplida("H-19", "motivo");
    partial void ValidarReglas(ConsultarElArriendoDatos datos)
    {
    }
}
