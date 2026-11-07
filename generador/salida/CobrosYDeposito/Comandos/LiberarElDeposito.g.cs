// Generado desde ArchiMate: ApplicationProcess "Liberar el depósito" (SB-20, id-e2968b9d61094a948605f2615f69fff0).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en LiberarElDeposito.cs.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada del comando "Liberar el depósito" (SB-20).</summary>
public sealed record LiberarElDeposito(
    string NumeroDelArriendo,
    decimal? ValorDeLosDanos,
    DateTime? HoraDeRegreso,
    DateOnly? FechaDeLaCancelacion
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record LiberarElDepositoDatos(
    LiberarElDeposito Comando,
    DepositoParaDanos DepositoParaDanos,
    DateOnly FechaDeLaLiberacion,
    CobrosPorLaPasarelaDePagosSalida CobrosPorLaPasarelaDePagos
);

/// <summary>Manejador del comando "Liberar el depósito" (SB-20).</summary>
/// <remarks>
/// <para>Contrato de servicio: Liberar el depósito (id-d0043dfa6a2d42c9ad9162ffe81bff2b), asociado al servicio de negocio
/// "Liberar el depósito" (id-61408d4df3f74394b564fefe5bfb6339), que el comando realiza.</para>
/// <para>Entrada: Arriendo e inspección sin daños, o arriendo cancelado con el depósito bloqueado.</para>
/// <para>Salida: Depósito liberado y fecha de la liberación.</para>
/// <para>Reglas: Se rechaza si la inspección registró daños (REG-01). Se libera en máximo 3 días después de la devolución (resultado de la V1). Si la reserva se cancela, se libera al cancelar, sin inspección (V4-SUP-09). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class LiberarElDepositoManejador(
    Repositorio<DepositoParaDanos> repositorio,
    BusDeEventos bus,
    ICobrosPorLaPasarelaDePagos cobrosPorLaPasarelaDePagos
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(LiberarElDepositoDatos datos);

    /// <summary>Dato calculado "fecha de la liberación" del comando: sale de hora de regreso, fecha de la cancelación. Se escribe en el archivo manual.</summary>
    private partial DateOnly FechaDeLaLiberacion(DateTime? horaDeRegreso, DateOnly? fechaDeLaCancelacion);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(LiberarElDeposito comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. Cargar la raíz.
        var depositoParaDanos = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe depósito para daños {comando.NumeroDelArriendo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Liberar el depósito", depositoParaDanos.Estado, EstadoDelDeposito.Bloqueado);

        // 2. Servicios SA que usa, en orden, y los datos calculados (archivo manual) en cuanto están sus datos.
        var calculadoFechaDeLaLiberacion = FechaDeLaLiberacion(comando.HoraDeRegreso, comando.FechaDeLaCancelacion);
        var respuestaCobrosPorLaPasarelaDePagos = cobrosPorLaPasarelaDePagos.Llamar(new CobrosPorLaPasarelaDePagosEntrada(TipoDeOrden.LiberacionDelDeposito, depositoParaDanos.NumeroDelArriendo, depositoParaDanos.ValorDelDeposito, null));

        // 4. Reglas del contrato (archivo manual).
        var datos = new LiberarElDepositoDatos(comando, depositoParaDanos, calculadoFechaDeLaLiberacion, respuestaCobrosPorLaPasarelaDePagos);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        depositoParaDanos.Estado = EstadoDelDeposito.Liberado;
        repositorio.Guardar(depositoParaDanos);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new DepositoLiberado(depositoParaDanos.NumeroDelArriendo, depositoParaDanos.ValorDelDeposito, calculadoFechaDeLaLiberacion), eventos);
        return new RespuestaDeComando(depositoParaDanos.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
