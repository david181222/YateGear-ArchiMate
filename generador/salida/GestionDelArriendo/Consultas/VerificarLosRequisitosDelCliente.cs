// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationService "Verificar los requisitos del cliente" (SB-11, id-8de1e624fe6d42b58cae281366f1e86a).
namespace YateGear.GestionDelArriendo;

public sealed partial class VerificarLosRequisitosDelClienteManejador
{
    // Reglas del "Contrato de servicio: Verificar los requisitos del cliente" (id-8dfaf8632e6042d3a86c8dcc1dbf95df):
    //   Se rechaza sin licencia de navegación vigente (H-09, NOR-01) o sin autorización del cliente para
    //   compartir sus datos con terceros (Ley 1581, H-19).
    //
    // Para rechazar la consulta:
    //   throw new ReglaIncumplida("H-19", "motivo");
    partial void ValidarReglas(VerificarLosRequisitosDelClienteDatos datos)
    {
    }

    // PENDIENTE: valor provisional de "cumple" (bool), dato calculado de la consulta.
    // Regla de la que sale: contrato SB-11, salida:
    //   Cumple o no cumple, con el motivo.
    private partial bool Cumple(VerificarLosRequisitosDelClienteDatos datos) => false;

    // PENDIENTE: valor provisional de "motivo" (string?), dato calculado de la consulta.
    // Regla de la que sale: contrato SB-11, salida:
    //   Cumple o no cumple, con el motivo.
    private partial string? Motivo(VerificarLosRequisitosDelClienteDatos datos) => null;
}
