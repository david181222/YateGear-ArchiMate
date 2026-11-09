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

    // "cumple" (bool), dato calculado de la consulta. Regla de la que sale: contrato SB-11, salida:
    //   Cumple o no cumple, con el motivo.
    // Escrito a mano: cumple si no le falta ningún requisito (ver Faltan).
    private partial bool Cumple(VerificarLosRequisitosDelClienteDatos datos) => Faltan(datos).Count == 0;

    // "motivo" (string?), dato calculado de la consulta. Regla de la que sale: contrato SB-11, salida:
    //   Cumple o no cumple, con el motivo.
    // Escrito a mano: los requisitos que faltan; null si cumple.
    private partial string? Motivo(VerificarLosRequisitosDelClienteDatos datos)
    {
        var faltan = Faltan(datos);
        return faltan.Count == 0 ? null : "No cumple: " + string.Join("; ", faltan) + ".";
    }

    // Escrito a mano: los requisitos de la ficha del cliente que guarda el arriendo (V6-SUP-01) que no se cumplen.
    private static List<string> Faltan(VerificarLosRequisitosDelClienteDatos datos)
    {
        var ficha = datos.Arriendo.FichaDelCliente;
        var faltan = new List<string>();
        // H-09, NOR-01: licencia vigente durante todo el arriendo (supuesto GEN-SUP-85: hasta su fin, sin la fecha de hoy).
        if (ficha.VigenciaDeLaLicencia < datos.Arriendo.FechasDelArriendo.Fin)
        {
            var vence = ficha.VigenciaDeLaLicencia.ToString("yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
            faltan.Add($"la licencia de navegación vence el {vence}, antes del fin del arriendo (H-09, NOR-01)");
        }
        // Ley 1581, H-19: autorización para compartir sus datos con terceros (la evaluadora y la aseguradora).
        if (ficha.TercerosAutorizados.Count == 0)
        {
            faltan.Add("el cliente no autorizó compartir sus datos con terceros (Ley 1581, H-19)");
        }
        return faltan;
    }
}
