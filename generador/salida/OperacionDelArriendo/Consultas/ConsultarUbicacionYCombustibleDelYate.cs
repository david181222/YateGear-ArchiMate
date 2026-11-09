// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationService "Consultar ubicación y combustible del yate" (SB-26, id-29d996ed0b0e4d8b8ba622da657f9388).
namespace YateGear.OperacionDelArriendo;

public sealed partial class ConsultarUbicacionYCombustibleDelYateManejador
{
    // Reglas del "Contrato de servicio: Consultar ubicación y combustible del yate" (id-c50f550246714ecaaff34411978a9538):
    //   Se rechaza si quien consulta no es el cliente del arriendo ni la marina que guarda el yate
    //   (V4-SUP-05).
    //
    // Para rechazar la consulta:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(ConsultarUbicacionYCombustibleDelYateDatos datos)
    {
        // Escrita a mano: solo con el arriendo en curso (acta de entrega sin acta de inspección, V8). V4-SUP-05 (quién
        // consulta) no se revisa: la aplicación no autentica a quien llama (GEN-SUP-46).
        var numero = datos.Consulta.NumeroDelArriendo;
        if (!datos.ActaDeEntrega.Any(a => a.NumeroDelArriendo == numero)
            || datos.ActaDeInspeccion.Any(a => a.NumeroDelArriendo == numero))
        {
            throw new ReglaIncumplida("V8", $"El arriendo {numero} no está en curso.");
        }
    }

    // Filtro de la lista que no es una igualdad (filtro_manual del YAML).
    // Regla de la que sale: contrato SB-26, reglas (arriba).
    // Escrito a mano: las lecturas del yate del arriendo, desde la entrega.
    private partial bool Incluir(ConsultarUbicacionYCombustibleDelYateDatos datos, LecturaDeUbicacionYCombustible lecturaDeUbicacionYCombustible)
    {
        var acta = datos.ActaDeEntrega.First(a => a.NumeroDelArriendo == datos.Consulta.NumeroDelArriendo);
        return lecturaDeUbicacionYCombustible.IdentificadorDelYate == acta.IdentificadorDelYate
            && lecturaDeUbicacionYCombustible.HoraDeLaLectura >= acta.HoraDeEntrega;
    }
}
