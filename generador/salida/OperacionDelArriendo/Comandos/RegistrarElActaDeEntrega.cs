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
        // H-13: declarada en el YAML (reglas); la revisa el código generado antes de llamar aquí.
        // CIE-01 (reserva confirmada) ya lo revisa "requiere".
    }
}
