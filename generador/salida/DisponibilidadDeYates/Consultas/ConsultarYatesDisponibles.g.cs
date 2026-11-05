// Generado desde ArchiMate: ApplicationService "Consultar yates disponibles" (SB-04, id-3c71d6c07530402bb5d436631366725d).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en ConsultarYatesDisponibles.cs.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Entrada de la consulta "Consultar yates disponibles" (SB-04).</summary>
public sealed record ConsultarYatesDisponibles(
    string IdentificadorDeLaMarina,
    DateOnly Inicio,
    DateOnly Fin
);

/// <summary>Un elemento de la lista que devuelve la consulta "Consultar yates disponibles": una raíz "Yate".</summary>
public sealed record ConsultarYatesDisponiblesElemento(
    string IdentificadorDelYate,
    string IdentificadorDeLaMarina,
    decimal PrecioPorDia
);

/// <summary>Salida de la consulta "Consultar yates disponibles".</summary>
public sealed record ConsultarYatesDisponiblesSalida(
    List<ConsultarYatesDisponiblesElemento> YatesDisponibles
);

/// <summary>Lo que reciben ValidarReglas, el filtro manual y los datos calculados: la consulta, las raíces
/// que cumplen el filtro y las demás raíces que lee la consulta.</summary>
public sealed record ConsultarYatesDisponiblesDatos(ConsultarYatesDisponibles Consulta, IReadOnlyList<Yate> Raices, IReadOnlyList<CalendarioDelYate> CalendarioDelYate);

/// <summary>Manejador de la consulta "Consultar yates disponibles" (SB-04). No cambia la raíz.</summary>
/// <remarks>
/// <para>Contrato de servicio: Consultar yates disponibles (id-bc45d7fbd4334ba79ca86892865b4f99), asociado al servicio de negocio
/// "Consultar yates disponibles" (id-01c956e2d271423d83b7b5db36d7511d).</para>
/// <para>Entrada: Ubicación del cliente o marina elegida, fecha de inicio y fecha de fin.</para>
/// <para>Salida: Lista de yates disponibles con su marina y su precio por día. Puede venir vacía.</para>
/// <para>Reglas: No se muestra un yate con esas fechas bloqueadas por el propietario o con otra reserva: disponible es sin bloqueo y sin otra reserva en esas fechas (H-08). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class ConsultarYatesDisponiblesManejador(Repositorio<Yate> repositorio, Repositorio<CalendarioDelYate> repositorioCalendarioDelYate)
{
    /// <summary>Reglas del contrato. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(ConsultarYatesDisponiblesDatos datos);

    /// <summary>Filtro que no es una igualdad (filtro_manual del YAML): true si la raíz va en la lista. Se escribe
    /// en el archivo manual.</summary>
    private partial bool Incluir(ConsultarYatesDisponiblesDatos datos, Yate yate);

    /// <summary>Ejecuta la consulta.</summary>
    public ConsultarYatesDisponiblesSalida Manejar(ConsultarYatesDisponibles consulta)
    {
        // Sobre todas las raíces que cumplen el filtro (filtro del YAML).
        var raices = repositorio.Todas().Where(yate => yate.IdentificadorDeLaMarina == consulta.IdentificadorDeLaMarina).ToList();
        var datos = new ConsultarYatesDisponiblesDatos(consulta, raices, repositorioCalendarioDelYate.Todas());
        ValidarReglas(datos);
        var elementos = raices.Where(yate => Incluir(datos, yate))
            .Select(yate => new ConsultarYatesDisponiblesElemento(yate.IdentificadorDelYate, yate.IdentificadorDeLaMarina, yate.PrecioPorDia))
            .ToList();
        return new ConsultarYatesDisponiblesSalida(
            elementos
        );
    }
}
