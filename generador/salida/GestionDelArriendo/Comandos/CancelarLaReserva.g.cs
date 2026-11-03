// Generado desde ArchiMate: ApplicationProcess "Cancelar la reserva" (SB-08, id-ea0f1874f954489589820b4aa2761e3f).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en CancelarLaReserva.cs.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada del comando "Cancelar la reserva" (SB-08).</summary>
public sealed record CancelarLaReserva(
    string NumeroDelArriendo,
    string QuienCancela,
    DateOnly FechaDeLaCancelacion
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record CancelarLaReservaDatos(
    CancelarLaReserva Comando,
    Arriendo Arriendo
);

/// <summary>Manejador del comando "Cancelar la reserva" (SB-08).</summary>
/// <remarks>
/// <para>Contrato de servicio: Cancelar la reserva (id-1b76f672e55f4171bc42f6e9e3700c3a), asociado al servicio de negocio
/// "Cancelar la reserva" (id-543ee022ee44497dbc49d870bc511326), que el comando realiza.</para>
/// <para>Entrada: Arriendo, quién cancela y fecha de la cancelación.</para>
/// <para>Salida: Arriendo cancelado y días de anticipación frente a la fecha de inicio.</para>
/// <para>Reglas: Se rechaza si el arriendo ya empezó: la cancelación es antes de la fecha del arriendo (EXC-02). La anticipación que da derecho a reembolso está en el contrato con el cliente (D-03). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class CancelarLaReservaManejador(
    Repositorio<Arriendo> repositorio,
    BusDeEventos bus
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(CancelarLaReservaDatos datos);

    /// <summary>Dato calculado "días de anticipación" del evento "Reserva cancelada". Se escribe en el archivo manual.</summary>
    private partial int DiasDeAnticipacion(CancelarLaReservaDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(CancelarLaReserva comando)
    {
        // 1. Cargar la raíz.
        var arriendo = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe arriendo {comando.NumeroDelArriendo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Cancelar la reserva", arriendo.Estado, EstadoDelArriendo.ReservaSolicitada, EstadoDelArriendo.ReservaConfirmada);

        // 4. Reglas del contrato (archivo manual).
        var datos = new CancelarLaReservaDatos(comando, arriendo);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        arriendo.Estado = EstadoDelArriendo.Cancelado;
        repositorio.Guardar(arriendo);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new ReservaCancelada(arriendo.NumeroDelArriendo, arriendo.YateDelArriendo.IdentificadorDelYate, arriendo.FechasDelArriendo.Inicio, arriendo.FechasDelArriendo.Fin, comando.FechaDeLaCancelacion, DiasDeAnticipacion(datos)), eventos);
        return new RespuestaDeComando(arriendo.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
