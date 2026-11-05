// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationService "Consultar yates disponibles" (SB-04, id-3c71d6c07530402bb5d436631366725d).
namespace YateGear.DisponibilidadDeYates;

public sealed partial class ConsultarYatesDisponiblesManejador
{
    // Reglas del "Contrato de servicio: Consultar yates disponibles" (id-bc45d7fbd4334ba79ca86892865b4f99):
    //   No se muestra un yate con esas fechas bloqueadas por el propietario o con otra reserva: disponible
    //   es sin bloqueo y sin otra reserva en esas fechas (H-08).
    //
    // Para rechazar la consulta:
    //   throw new ReglaIncumplida("H-19", "motivo");
    partial void ValidarReglas(ConsultarYatesDisponiblesDatos datos)
    {
    }

    // H-08, escrita a mano: disponible es sin bloqueo y sin otra reserva en esas fechas. Un yate sin calendario
    // tiene todas sus fechas libres (V6-SUP-03).
    private partial bool Incluir(ConsultarYatesDisponiblesDatos datos, Yate yate)
    {
        var consulta = datos.Consulta;
        var calendario = datos.CalendarioDelYate.FirstOrDefault(c => c.IdentificadorDelYate == yate.IdentificadorDelYate);
        return calendario is null
            || !calendario.RangoDeFechas.Any(r => r.Inicio <= consulta.Fin && consulta.Inicio <= r.Fin);
    }
}
