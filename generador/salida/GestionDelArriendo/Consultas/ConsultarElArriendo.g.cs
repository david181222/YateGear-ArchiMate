// Generado desde ArchiMate: ApplicationService "Consultar el arriendo" (SB-10, id-ed6830eac52c4d5aa7983fb1edd63869).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en ConsultarElArriendo.cs.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada de la consulta "Consultar el arriendo" (SB-10).</summary>
public sealed record ConsultarElArriendo(
    string NumeroDelArriendo
);

/// <summary>Salida de la consulta "Consultar el arriendo".</summary>
public sealed record ConsultarElArriendoSalida(
    string ReferenciaAlCRM,
    string IdentificadorDelYate,
    string Marina,
    DateOnly Inicio,
    DateOnly Fin,
    EstadoDelArriendo Estado
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: la consulta y la raíz.</summary>
public sealed record ConsultarElArriendoDatos(ConsultarElArriendo Consulta, Arriendo Arriendo);

/// <summary>Manejador de la consulta "Consultar el arriendo" (SB-10). No cambia la raíz.</summary>
/// <remarks>
/// <para>Contrato de servicio: Consultar el arriendo (id-cd8962c3c6d44cfb927557b1a4e45e53), asociado al servicio de negocio
/// "Consultar el arriendo" (id-47df454247c847e0be29ca1bb86c09af).</para>
/// <para>Entrada: Número de arriendo.</para>
/// <para>Salida: Cliente, yate, marina, fechas y estado del arriendo.</para>
/// <para>Reglas: Se rechaza si quien consulta no participa en el arriendo, porque son datos personales del cliente (Ley 1581, H-19). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class ConsultarElArriendoManejador(Repositorio<Arriendo> repositorio)
{
    /// <summary>Reglas del contrato. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(ConsultarElArriendoDatos datos);

    /// <summary>Ejecuta la consulta.</summary>
    public ConsultarElArriendoSalida Manejar(ConsultarElArriendo consulta)
    {
        var arriendo = repositorio.Obtener(consulta.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe arriendo {consulta.NumeroDelArriendo}.");
        var datos = new ConsultarElArriendoDatos(consulta, arriendo);
        ValidarReglas(datos);
        return new ConsultarElArriendoSalida(
            arriendo.FichaDelCliente.ReferenciaAlCRM,
            arriendo.YateDelArriendo.IdentificadorDelYate,
            arriendo.YateDelArriendo.Marina,
            arriendo.FechasDelArriendo.Inicio,
            arriendo.FechasDelArriendo.Fin,
            arriendo.Estado
        );
    }
}
