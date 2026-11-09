// Generado desde ArchiMate: ApplicationComponent "Contexto Cobros y depósito" (id-859686865fd4465397859188d62c971c).
// Capa 3: recibe los eventos de otros contextos y dispara el comando de este contexto
// (eventos_de_otros_contextos del YAML). No editar: el generador reescribe este archivo.
#nullable enable
using System.Text.Json;

namespace YateGear.CobrosYDeposito;

/// <summary>Recibe los eventos de otros contextos. Si un evento tiene junto_con, espera a que lleguen todos
/// los de su grupo (en memoria, por identidad) y entonces dispara el comando con los datos de todos.</summary>
public sealed class ReceptorDeEventosExternos(
    Bitacora bitacora,
    DescontarDanosDelDepositoManejador descontarDanosDelDeposito,
    LiberarElDepositoManejador liberarElDeposito,
    LiquidarYCobrarLosCargosDelCierreManejador liquidarYCobrarLosCargosDelCierre,
    ReembolsarUnaCancelacionManejador reembolsarUnaCancelacion,
    Repositorio<CuentaDelArriendo> repositorioCuentaDelArriendo,
    Repositorio<DepositoParaDanos> repositorioDepositoParaDanos
)
{
    /// <summary>"Diferencias determinadas" de "Contexto Operación del arriendo" (id-497addd0bf144aed8bf9f4ba01d7eac3). Dispara "Liquidar y cobrar los cargos del cierre", "Liberar el depósito" (si se cumple su condición), "Descontar daños del depósito" (si se cumple su condición).</summary>
    public RespuestaDeEventoExterno Recibir(DiferenciasDeterminadas evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        // Dispara varios comandos, en orden; si uno falla, los siguientes no corren.
        var respuestas = new List<RespuestaDeComando>();
        respuestas.Add(liquidarYCobrarLosCargosDelCierre.Manejar(new LiquidarYCobrarLosCargosDelCierre(evento.NumeroDelArriendo, evento.CombustibleConsumido, evento.HorasAdicionales, evento.Evidencia, evento.HoraDeRegreso)));
        if ((evento.ValorDeLosDanos == 0m))
        {
            respuestas.Add(liberarElDeposito.Manejar(new LiberarElDeposito(evento.NumeroDelArriendo, evento.ValorDeLosDanos, evento.HoraDeRegreso, null)));
        }
        if (!(evento.ValorDeLosDanos == 0m))
        {
            respuestas.Add(descontarDanosDelDeposito.Manejar(new DescontarDanosDelDeposito(evento.NumeroDelArriendo, evento.ValorDeLosDanos, evento.Evidencia)));
        }
        return RespuestaDeEventoExterno.Ejecutado(RespuestaDeComando.Juntar(evento.Identidad, respuestas));
    }

    /// <summary>Lee "Diferencias determinadas" desde JSON y lo recibe. Si falta un dato obligatorio, DatoFaltante (422).</summary>
    public RespuestaDeEventoExterno RecibirDiferenciasDeterminadas(JsonElement json) =>
        Recibir(LectorDeEventos.Leer<DiferenciasDeterminadas>(json, ("numeroDelArriendo", "número del arriendo"), ("horaDeRegreso", "hora de regreso"), ("combustibleConsumido", "combustible consumido"), ("horasAdicionales", "horas adicionales"), ("valorDeLosDanos", "valor de los daños"), ("evidencia", "evidencia")));

    /// <summary>"Reserva cancelada" de "Contexto Gestión del arriendo" (id-28e06fd82a7641228d89ded443509b64). Dispara "Liberar el depósito" (si se cumple su condición), "Reembolsar una cancelación" (si se cumple su condición).</summary>
    public RespuestaDeEventoExterno Recibir(ReservaCancelada evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        // Dispara varios comandos, en orden; si uno falla, los siguientes no corren.
        var respuestas = new List<RespuestaDeComando>();
        if (repositorioDepositoParaDanos.Obtener(evento.NumeroDelArriendo) is not null)
        {
            respuestas.Add(liberarElDeposito.Manejar(new LiberarElDeposito(evento.NumeroDelArriendo, null, null, evento.FechaDeLaCancelacion)));
        }
        if (repositorioCuentaDelArriendo.Obtener(evento.NumeroDelArriendo) is not null)
        {
            respuestas.Add(reembolsarUnaCancelacion.Manejar(new ReembolsarUnaCancelacion(evento.NumeroDelArriendo, evento.DiasDeAnticipacion)));
        }
        return RespuestaDeEventoExterno.Ejecutado(RespuestaDeComando.Juntar(evento.Identidad, respuestas));
    }

    /// <summary>Lee "Reserva cancelada" desde JSON y lo recibe. Si falta un dato obligatorio, DatoFaltante (422).</summary>
    public RespuestaDeEventoExterno RecibirReservaCancelada(JsonElement json) =>
        Recibir(LectorDeEventos.Leer<ReservaCancelada>(json, ("numeroDelArriendo", "número del arriendo"), ("fechaDeLaCancelacion", "fecha de la cancelación"), ("diasDeAnticipacion", "días de anticipación")));
}
