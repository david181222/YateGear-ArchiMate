// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Gestionar la ocupación del calendario" (SB-05, id-91e23dd9dfb741b79a6f487952bd22c0).
namespace YateGear.DisponibilidadDeYates;

public sealed partial class GestionarLaOcupacionDelCalendarioManejador
{
    // Reglas del "Contrato de servicio: Gestionar la ocupación del calendario" (id-683b3fd66779488b96a331df7112516d):
    //   Se rechaza apartar u ocupar fechas que ya tiene otro arriendo o que bloqueó el propietario: un yate
    //   no puede tener dos arriendos en las mismas fechas (REG-01). Las fechas se apartan al pedir la
    //   reserva y se ocupan al confirmarla (V4-SUP-01).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("REG-01", "motivo");
    partial void ValidarReglas(GestionarLaOcupacionDelCalendarioDatos datos)
    {
        // REG-01, escrita a mano: no se apartan ni se ocupan fechas que se cruzan con las de otro arriendo o con un
        // bloqueo del propietario (un rango bloqueado no tiene número del arriendo).
        var comando = datos.Comando;
        if (datos.Resultado is GestionarLaOcupacionDelCalendarioResultado.FechasApartadas
                or GestionarLaOcupacionDelCalendarioResultado.FechasOcupadas
            && datos.CalendarioDelYate.RangoDeFechas.Any(r => r.NumeroDelArriendo != comando.NumeroDelArriendo
                                                              && r.Inicio <= comando.Fin && comando.Inicio <= r.Fin))
        {
            throw new ReglaIncumplida("REG-01", "Un yate no puede tener dos arriendos en las mismas fechas, ni un arriendo en fechas bloqueadas.");
        }
    }
}
