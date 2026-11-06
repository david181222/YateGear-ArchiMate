// Generado desde ArchiMate: ApplicationProcess "Confirmar la reserva" (SB-07, id-b5e59d3c453a410580107b2287cd76d2).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en ConfirmarLaReserva.cs.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada del comando "Confirmar la reserva" (SB-07).</summary>
public sealed record ConfirmarLaReserva(
    string NumeroDelArriendo,
    string ComprobanteDelAlquiler,
    string ComprobanteDelSeguro,
    string AutorizacionDelBloqueoDelDeposito
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record ConfirmarLaReservaDatos(
    ConfirmarLaReserva Comando,
    Arriendo Arriendo,
    ContratosConPropietariosYClientesSalida ContratosConPropietariosYClientes
);

/// <summary>Manejador del comando "Confirmar la reserva" (SB-07).</summary>
/// <remarks>
/// <para>Contrato de servicio: Confirmar la reserva (id-684d5b92ffbb4fefa001d8936128713c), asociado al servicio de negocio
/// "Confirmar la reserva" (id-c29fef62efa041a09a0f1f449fc65e11), que el comando realiza.</para>
/// <para>Entrada: Arriendo, evaluación de riesgo aceptable, referencia del contrato firmado, comprobantes del alquiler y del seguro y autorización del bloqueo del depósito.</para>
/// <para>Salida: Arriendo en estado reserva confirmada.</para>
/// <para>Reglas: No se confirma sin riesgo aceptable, contrato firmado y pagos completos (REG-01); si falta uno, se rechaza indicando cuál. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class ConfirmarLaReservaManejador(
    Repositorio<Arriendo> repositorio,
    BusDeEventos bus,
    IContratosConPropietariosYClientes contratosConPropietariosYClientes
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(ConfirmarLaReservaDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(ConfirmarLaReserva comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. Cargar la raíz.
        var arriendo = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe arriendo {comando.NumeroDelArriendo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Confirmar la reserva", arriendo.Estado, EstadoDelArriendo.ReservaSolicitada);

        // 2. Servicios SA que usa, en orden.
        var respuestaContratosConPropietariosYClientes = contratosConPropietariosYClientes.Llamar(new ContratosConPropietariosYClientesEntrada(arriendo.NumeroDelArriendo));

        // 4. Reglas del contrato (archivo manual).
        var datos = new ConfirmarLaReservaDatos(comando, arriendo, respuestaContratosConPropietariosYClientes);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        arriendo.ReferenciaDelContratoFirmado = respuestaContratosConPropietariosYClientes.ReferenciaDelContratoFirmado;
        arriendo.PruebasDePago = new PruebasDePago(comando.ComprobanteDelAlquiler, comando.ComprobanteDelSeguro, comando.AutorizacionDelBloqueoDelDeposito);
        arriendo.Estado = EstadoDelArriendo.ReservaConfirmada;
        repositorio.Guardar(arriendo);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new ReservaConfirmada(arriendo.NumeroDelArriendo, arriendo.YateDelArriendo.IdentificadorDelYate, arriendo.FechasDelArriendo.Inicio, arriendo.FechasDelArriendo.Fin), eventos);
        return new RespuestaDeComando(arriendo.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
