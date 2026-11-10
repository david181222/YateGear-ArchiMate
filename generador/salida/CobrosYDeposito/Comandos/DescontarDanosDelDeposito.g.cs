// Generado desde ArchiMate: ApplicationProcess "Descontar daños del depósito" (SB-21, id-53533cc505c540bbafcb8473107780c3).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en DescontarDanosDelDeposito.cs.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada del comando "Descontar daños del depósito" (SB-21).</summary>
public sealed record DescontarDanosDelDeposito(
    string NumeroDelArriendo,
    decimal ValorDeLosDanos,
    List<string> Evidencia
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record DescontarDanosDelDepositoDatos(
    DescontarDanosDelDeposito Comando,
    DepositoParaDanos DepositoParaDanos,
    decimal ValorDescontadoDelDeposito,
    decimal SaldoLiberado,
    decimal ValorQueExcedeElDeposito,
    CobrosPorLaPasarelaDePagosSalida CobrosPorLaPasarelaDePagos
);

/// <summary>Manejador del comando "Descontar daños del depósito" (SB-21).</summary>
/// <remarks>
/// <para>Contrato de servicio: Descontar daños del depósito (id-31ee84a6c3c14f06908a6b41dce32745), asociado al servicio de negocio
/// "Descontar daños del depósito" (id-1164ab8441854cb79fc5e1e191a3483f), que el comando realiza.</para>
/// <para>Entrada: Arriendo, valor de los daños y evidencia.</para>
/// <para>Salida: Valor descontado, saldo liberado y valor que excede el depósito, si lo hay.</para>
/// <para>Reglas: Se rechaza un descuento sin evidencia (principio "Todo cobro va con evidencia", V1). Se hace en máximo 3 días después de la devolución (resultado de la V1). El valor de los daños llega con la inspección (V4-SUP-03). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class DescontarDanosDelDepositoManejador(
    Repositorio<DepositoParaDanos> repositorio,
    BusDeEventos bus,
    ICobrosPorLaPasarelaDePagos cobrosPorLaPasarelaDePagos
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(DescontarDanosDelDepositoDatos datos);

    /// <summary>Dato calculado "valor descontado del depósito" del comando: sale de valor de los daños, valor del depósito. Se escribe en el archivo manual.</summary>
    private partial decimal ValorDescontadoDelDeposito(decimal valorDeLosDanos, decimal valorDelDeposito);

    /// <summary>Dato calculado "saldo liberado" del comando: sale de valor de los daños, valor del depósito. Se escribe en el archivo manual.</summary>
    private partial decimal SaldoLiberado(decimal valorDeLosDanos, decimal valorDelDeposito);

    /// <summary>Dato calculado "valor que excede el depósito" del comando: sale de valor de los daños, valor del depósito. Se escribe en el archivo manual.</summary>
    private partial decimal ValorQueExcedeElDeposito(decimal valorDeLosDanos, decimal valorDelDeposito);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(DescontarDanosDelDeposito comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. Cargar la raíz.
        var depositoParaDanos = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe depósito para daños {comando.NumeroDelArriendo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Descontar daños del depósito", depositoParaDanos.Estado, EstadoDelDeposito.Bloqueado);

        // 2. Servicios SA que usa, en orden, y los datos calculados (archivo manual) en cuanto están sus datos.
        var calculadoValorDescontadoDelDeposito = ValorDescontadoDelDeposito(comando.ValorDeLosDanos, depositoParaDanos.ValorDelDeposito);
        var calculadoSaldoLiberado = SaldoLiberado(comando.ValorDeLosDanos, depositoParaDanos.ValorDelDeposito);
        var calculadoValorQueExcedeElDeposito = ValorQueExcedeElDeposito(comando.ValorDeLosDanos, depositoParaDanos.ValorDelDeposito);
        var respuestaCobrosPorLaPasarelaDePagos = cobrosPorLaPasarelaDePagos.Llamar(new CobrosPorLaPasarelaDePagosEntrada(TipoDeOrden.DescuentoDelDeposito, depositoParaDanos.NumeroDelArriendo, calculadoValorDescontadoDelDeposito, null));

        // 4. Reglas del contrato declaradas en el YAML (reglas), en orden.
        if (comando.Evidencia is not { Count: > 0 })
        {
            throw new ReglaIncumplida("V1", "Todo cobro va con evidencia: el descuento no trae las fotos de la inspección.");
        }
        if ((comando.ValorDeLosDanos <= 0m))
        {
            throw new ReglaIncumplida("REG-01", "La inspección no registró daños: el depósito se libera, no se descuenta.");
        }
        if (!(respuestaCobrosPorLaPasarelaDePagos.Aprobada == true))
        {
            throw new ReglaIncumplida("INT-PAG", "La pasarela no aprobó el descuento del depósito.");
        }

        // 4b. Las demás reglas del contrato (archivo manual).
        var datos = new DescontarDanosDelDepositoDatos(comando, depositoParaDanos, calculadoValorDescontadoDelDeposito, calculadoSaldoLiberado, calculadoValorQueExcedeElDeposito, respuestaCobrosPorLaPasarelaDePagos);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        depositoParaDanos.EvidenciaDelDescuento = comando.Evidencia;
        depositoParaDanos.Estado = EstadoDelDeposito.Descontado;
        repositorio.Guardar(depositoParaDanos);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new DanosDescontadosDelDeposito(depositoParaDanos.NumeroDelArriendo, comando.ValorDeLosDanos, calculadoValorDescontadoDelDeposito, calculadoSaldoLiberado, calculadoValorQueExcedeElDeposito, comando.Evidencia), eventos);
        return new RespuestaDeComando(depositoParaDanos.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
