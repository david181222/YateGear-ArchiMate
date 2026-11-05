// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Detectar la pérdida de señal" (SB-27, id-c742e57f7d34406c8162646ca3080c19).
namespace YateGear.OperacionDelArriendo;

public sealed partial class DetectarLaPerdidaDeSenalManejador
{
    // Reglas del "Contrato de servicio: Detectar la pérdida de señal" (id-28e93eb31c154c3dacd73eaf420c10ce):
    //   El tiempo sin lecturas que dispara la alerta lo fija Operaciones (V4-SUP-04). Contactar al cliente
    //   lo hace la marina; el software solo detecta y avisa (EXC-01).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(DetectarLaPerdidaDeSenalDatos datos)
    {
    }

    // PENDIENTE: las raíces por las que se publica un evento (comando sobre todas). Por ahora, ninguna.
    // Regla de la que sale: contrato SB-27, reglas (arriba).
    // Escrito a mano (SB-27): para cada yate con arriendo en curso (acta de entrega sin acta de inspección, V8), su
    // última lectura si tiene más minutos de los permitidos. Un yate sin lecturas no tiene "última lectura conocida"
    // y no se elige (supuesto GEN-SUP-50). Se avisa en cada revisión mientras no lleguen lecturas (GEN-SUP-51).
    private partial IEnumerable<LecturaDeUbicacionYCombustible> Seleccionar(DetectarLaPerdidaDeSenalDatos datos)
    {
        var limite = datos.Comando.Ahora.AddMinutes(-datos.Comando.MinutosSinLecturas);
        var devueltos = datos.ActaDeInspeccion.Select(a => a.NumeroDelArriendo).ToHashSet();
        foreach (var acta in datos.ActaDeEntrega.Where(a => !devueltos.Contains(a.NumeroDelArriendo)))
        {
            var ultima = datos.Raices.Where(l => l.IdentificadorDelYate == acta.IdentificadorDelYate)
                                     .MaxBy(l => l.HoraDeLaLectura);
            if (ultima is not null && ultima.HoraDeLaLectura < limite)
            {
                yield return ultima;
            }
        }
    }
}
