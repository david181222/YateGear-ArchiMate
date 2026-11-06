// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Registrar el acta de entrega" (SB-22, id-8addfcc26ad744b8a15ea09a54227d4d).
namespace YateGear.OperacionDelArriendo;

public sealed partial class RegistrarElActaDeEntregaManejador
{
    // Reglas del "Contrato de servicio: Registrar el acta de entrega" (id-cebe80de47aa4662af8631258f3353b5):
    //   Se rechaza si el arriendo no tiene la reserva confirmada (CIE-01) o si el acta no trae fotos (H-13).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(RegistrarElActaDeEntregaDatos datos)
    {
        // H-13, escrita a mano: el acta debe traer fotos. CIE-01 (reserva confirmada) ya lo revisa "requiere".
        if (datos.Comando.Fotos is null || datos.Comando.Fotos.Count == 0)
        {
            throw new ReglaIncumplida("H-13", "El acta de entrega no trae fotos.");
        }
    }
}
