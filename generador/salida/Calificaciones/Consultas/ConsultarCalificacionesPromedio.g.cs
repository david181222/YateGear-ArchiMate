// Generado desde ArchiMate: ApplicationService "Consultar calificaciones promedio" (SB-30, id-f3d1d639b7ec477aa112072ed01dd0f4).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en ConsultarCalificacionesPromedio.cs.
#nullable enable
namespace YateGear.Calificaciones;

/// <summary>Entrada de la consulta "Consultar calificaciones promedio" (SB-30).</summary>
public sealed record ConsultarCalificacionesPromedio(
    string Calificado
);

/// <summary>Salida de la consulta "Consultar calificaciones promedio".</summary>
public sealed record ConsultarCalificacionesPromedioSalida(
    decimal? CalificacionPromedio,
    int NumeroDeCalificaciones
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: la consulta y las raíces
/// que cumplen el filtro.</summary>
public sealed record ConsultarCalificacionesPromedioDatos(ConsultarCalificacionesPromedio Consulta, IReadOnlyList<Calificacion> Raices);

/// <summary>Manejador de la consulta "Consultar calificaciones promedio" (SB-30). No cambia la raíz.</summary>
/// <remarks>
/// <para>Contrato de servicio: Consultar calificaciones promedio (id-4227bf7b674d46d4b77aa11bd3e6a029), asociado al servicio de negocio
/// "Consultar calificaciones promedio" (id-4ab0c68883be4f879f9e0da5f2d83334).</para>
/// <para>Entrada: Propietario o cliente.</para>
/// <para>Salida: Calificación promedio y número de calificaciones.</para>
/// <para>Reglas: el contrato no tiene reglas. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class ConsultarCalificacionesPromedioManejador(Repositorio<Calificacion> repositorio)
{
    /// <summary>Reglas del contrato. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(ConsultarCalificacionesPromedioDatos datos);

    /// <summary>Ejecuta la consulta.</summary>
    public ConsultarCalificacionesPromedioSalida Manejar(ConsultarCalificacionesPromedio consulta)
    {
        // Sobre todas las raíces que cumplen el filtro (filtro del YAML).
        var raices = repositorio.Todas().Where(calificacion => calificacion.Calificado == consulta.Calificado).ToList();
        var datos = new ConsultarCalificacionesPromedioDatos(consulta, raices);
        ValidarReglas(datos);
        return new ConsultarCalificacionesPromedioSalida(
            raices.Count == 0 ? null : (decimal?)raices.Average(calificacion => (decimal)calificacion.CalificacionDada),
            raices.Count
        );
    }
}
