// Generado desde ArchiMate: ApplicationProcess "Bloquear el depósito" (SB-19, id-43d3a21049834a9ea5e2f3f8b3079d0a).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en BloquearElDeposito.cs.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada del comando "Bloquear el depósito" (SB-19).</summary>
public sealed record BloquearElDeposito(
    string NumeroDelArriendo,
    decimal ValorDelDeposito,
    string MedioDePago,
    DateOnly Fin
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record BloquearElDepositoDatos(
    BloquearElDeposito Comando,
    CobrosPorLaPasarelaDePagosSalida CobrosPorLaPasarelaDePagos
);

/// <summary>Manejador del comando "Bloquear el depósito" (SB-19).</summary>
/// <remarks>
/// <para>Contrato de servicio: Bloquear el depósito (id-be586e0ecad5498c8973ace01690688c), asociado al servicio de negocio
/// "Bloquear el depósito" (id-b3842577622441589b72e66a331ff25d), que el comando realiza.</para>
/// <para>Entrada: Arriendo, valor del depósito y tarjeta de crédito del cliente.</para>
/// <para>Salida: Depósito bloqueado con su código de autorización y la fecha en que vence el bloqueo.</para>
/// <para>Reglas: Se rechaza si el bloqueo vencería antes del cierre: la autorización en tarjeta de crédito dura 28 días (V4-SUP-07, contraste de H-10). En la práctica, la fecha de fin del arriendo no puede pasar de unos 25 días después de reservar. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class BloquearElDepositoManejador(
    Repositorio<DepositoParaDanos> repositorio,
    BusDeEventos bus,
    ICobrosPorLaPasarelaDePagos cobrosPorLaPasarelaDePagos
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(BloquearElDepositoDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(BloquearElDeposito comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 2. Servicios SA que usa, en orden.
        var respuestaCobrosPorLaPasarelaDePagos = cobrosPorLaPasarelaDePagos.Llamar(new CobrosPorLaPasarelaDePagosEntrada(TipoDeOrden.BloqueoDelDeposito, comando.NumeroDelArriendo, comando.ValorDelDeposito, comando.MedioDePago));

        // 4. Reglas del contrato declaradas en el YAML (reglas), en orden.
        if (!(respuestaCobrosPorLaPasarelaDePagos.Aprobada == true))
        {
            throw new ReglaIncumplida("INT-PAG", "La pasarela no aprobó el bloqueo del depósito.");
        }

        // 4b. Las demás reglas del contrato (archivo manual).
        var datos = new BloquearElDepositoDatos(comando, respuestaCobrosPorLaPasarelaDePagos);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Su identidad se forma con datos;
        //    si ya existe una raíz con esa identidad, 409.
        var depositoParaDanos = new DepositoParaDanos
        {
            Estado = EstadoDelDeposito.Bloqueado,
            ValorDelDeposito = comando.ValorDelDeposito,
            CodigoDeAutorizacionDeLaPasarela = respuestaCobrosPorLaPasarelaDePagos.Comprobante,
            FechaDeVencimientoDelBloqueo = (respuestaCobrosPorLaPasarelaDePagos.VencimientoDelBloqueo ?? throw new DatoFaltante("fecha de vencimiento del bloqueo")),
        };
        repositorio.Agregar(depositoParaDanos, $"{(comando.NumeroDelArriendo)}");

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new DepositoBloqueado(depositoParaDanos.NumeroDelArriendo, respuestaCobrosPorLaPasarelaDePagos.Comprobante, (respuestaCobrosPorLaPasarelaDePagos.VencimientoDelBloqueo ?? throw new DatoFaltante("fecha de vencimiento del bloqueo"))), eventos);
        return new RespuestaDeComando(depositoParaDanos.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
