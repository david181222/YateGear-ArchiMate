// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Devolver el libro" (SB-02, id-5bf799b38b425df3b814b33aa2929f70).
namespace Biblioteca.Prestamos;

public sealed partial class DevolverElLibroManejador
{
    // Reglas del "Contrato de servicio: Devolver el libro" (id-be012cf9cf7a573c8176e8e3dadd4814):
    //   Solo se devuelve un libro prestado.
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(DevolverElLibroDatos datos)
    {
    }
}
