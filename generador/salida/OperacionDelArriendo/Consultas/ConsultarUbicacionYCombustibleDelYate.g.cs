// Generado desde ArchiMate: ApplicationService "Consultar ubicación y combustible del yate" (SB-26, id-29d996ed0b0e4d8b8ba622da657f9388).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en ConsultarUbicacionYCombustibleDelYate.cs.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Entrada de la consulta "Consultar ubicación y combustible del yate" (SB-26).</summary>
public sealed record ConsultarUbicacionYCombustibleDelYate(
    string NumeroDelArriendo
);

/// <summary>Un elemento de la lista que devuelve la consulta "Consultar ubicación y combustible del yate": una raíz "Lectura de ubicación y combustible".</summary>
public sealed record ConsultarUbicacionYCombustibleDelYateElemento(
    decimal Latitud,
    decimal Longitud,
    decimal NivelDeCombustible,
    DateTime HoraDeLaLectura
);

/// <summary>Salida de la consulta "Consultar ubicación y combustible del yate".</summary>
public sealed record ConsultarUbicacionYCombustibleDelYateSalida(
    List<ConsultarUbicacionYCombustibleDelYateElemento> Recorrido
);

/// <summary>Lo que reciben ValidarReglas, el filtro manual y los datos calculados: la consulta, las raíces
/// que cumplen el filtro y las demás raíces que lee la consulta.</summary>
public sealed record ConsultarUbicacionYCombustibleDelYateDatos(ConsultarUbicacionYCombustibleDelYate Consulta, IReadOnlyList<LecturaDeUbicacionYCombustible> Raices, IReadOnlyList<ActaDeEntrega> ActaDeEntrega, IReadOnlyList<ActaDeInspeccion> ActaDeInspeccion);

/// <summary>Manejador de la consulta "Consultar ubicación y combustible del yate" (SB-26). No cambia la raíz.</summary>
/// <remarks>
/// <para>Contrato de servicio: Consultar ubicación y combustible del yate (id-c50f550246714ecaaff34411978a9538), asociado al servicio de negocio
/// "Consultar ubicación y combustible del yate" (id-b5801260aedb4028ba4325e1eed2900b).</para>
/// <para>Entrada: Arriendo en curso y quién consulta.</para>
/// <para>Salida: Última posición, nivel de combustible, hora y recorrido.</para>
/// <para>Reglas: Se rechaza si quien consulta no es el cliente del arriendo ni la marina que guarda el yate (V4-SUP-05). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class ConsultarUbicacionYCombustibleDelYateManejador(Repositorio<LecturaDeUbicacionYCombustible> repositorio, Repositorio<ActaDeEntrega> repositorioActaDeEntrega, Repositorio<ActaDeInspeccion> repositorioActaDeInspeccion)
{
    /// <summary>Reglas del contrato. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(ConsultarUbicacionYCombustibleDelYateDatos datos);

    /// <summary>Filtro que no es una igualdad (filtro_manual del YAML): true si la raíz va en la lista. Se escribe
    /// en el archivo manual.</summary>
    private partial bool Incluir(ConsultarUbicacionYCombustibleDelYateDatos datos, LecturaDeUbicacionYCombustible lecturaDeUbicacionYCombustible);

    /// <summary>Ejecuta la consulta.</summary>
    public ConsultarUbicacionYCombustibleDelYateSalida Manejar(ConsultarUbicacionYCombustibleDelYate consulta)
    {
        // Sobre todas las raíces que cumplen el filtro (filtro del YAML).
        var raices = repositorio.Todas().Where(lecturaDeUbicacionYCombustible => true).ToList();
        var datos = new ConsultarUbicacionYCombustibleDelYateDatos(consulta, raices, repositorioActaDeEntrega.Todas(), repositorioActaDeInspeccion.Todas());
        ValidarReglas(datos);
        var elementos = raices.Where(lecturaDeUbicacionYCombustible => Incluir(datos, lecturaDeUbicacionYCombustible))
            .OrderBy(lecturaDeUbicacionYCombustible => lecturaDeUbicacionYCombustible.HoraDeLaLectura)
            .Select(lecturaDeUbicacionYCombustible => new ConsultarUbicacionYCombustibleDelYateElemento(lecturaDeUbicacionYCombustible.Latitud, lecturaDeUbicacionYCombustible.Longitud, lecturaDeUbicacionYCombustible.NivelDeCombustible, lecturaDeUbicacionYCombustible.HoraDeLaLectura))
            .ToList();
        return new ConsultarUbicacionYCombustibleDelYateSalida(
            elementos
        );
    }
}
