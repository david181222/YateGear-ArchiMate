// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Prestar un libro" (SB-01, id-adbef6a6733f58f5a9e0ba51f136a4ac).
namespace Biblioteca.Prestamos;

public sealed partial class PrestarUnLibroManejador
{
    // Reglas del "Contrato de servicio: Prestar un libro" (id-ae3bbf116893597ab208483228f70381):
    //   REG-01: se rechaza si el catálogo dice que el libro no está disponible.
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(PrestarUnLibroDatos datos)
    {
        // Escrito a mano: la respuesta del catálogo (SA-01) llega en los datos del comando.
        if (!datos.CatalogoDeLaBiblioteca.Disponible)
        {
            throw new ReglaIncumplida("REG-01", "El catálogo dice que el libro no está disponible.");
        }
    }
}
