// Generado desde ArchiMate: ApplicationProcess "Liquidar y cobrar los cargos del cierre" (SB-14, id-3101c7184ff44fbfb862a7645b4e6135).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en LiquidarYCobrarLosCargosDelCierre.cs.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada del comando "Liquidar y cobrar los cargos del cierre" (SB-14).</summary>
public sealed record LiquidarYCobrarLosCargosDelCierre(
    string NumeroDelArriendo,
    decimal CombustibleConsumido,
    decimal HorasAdicionales,
    List<string> Evidencia,
    DateTime HoraDeRegreso
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record LiquidarYCobrarLosCargosDelCierreDatos(
    LiquidarYCobrarLosCargosDelCierre Comando,
    CuentaDelArriendo CuentaDelArriendo,
    decimal ValorDelCombustible,
    decimal ValorDelTiempoAdicional,
    bool HayTiempoAdicional,
    CobrosPorLaPasarelaDePagosSalida CobrosPorLaPasarelaDePagos1,
    CobrosPorLaPasarelaDePagosSalida? CobrosPorLaPasarelaDePagos2
);

/// <summary>Manejador del comando "Liquidar y cobrar los cargos del cierre" (SB-14).</summary>
/// <remarks>
/// <para>Contrato de servicio: Liquidar y cobrar los cargos del cierre (id-b7171db9da564944bab35b3666ab3c83), asociado al servicio de negocio
/// "Liquidar y cobrar los cargos del cierre" (id-ba00d438a249424ab172d10850c7bf19), que el comando realiza.</para>
/// <para>Entrada: Arriendo, combustible consumido, horas adicionales y evidencia (actas y fotos de entrega e inspección).</para>
/// <para>Salida: Cargos cobrados con su comprobante y la evidencia que los respalda.</para>
/// <para>Reglas: Se rechaza un cargo sin evidencia (principio "Todo cobro va con evidencia", V1). El combustible consumido siempre lo paga el cliente (REG-01). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class LiquidarYCobrarLosCargosDelCierreManejador(
    Repositorio<CuentaDelArriendo> repositorio,
    BusDeEventos bus,
    ICobrosPorLaPasarelaDePagos cobrosPorLaPasarelaDePagos
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(LiquidarYCobrarLosCargosDelCierreDatos datos);

    /// <summary>Dato calculado "valor del combustible" del comando: sale de combustible consumido. Se escribe en el archivo manual.</summary>
    private partial decimal ValorDelCombustible(decimal combustibleConsumido);

    /// <summary>Dato calculado "valor del tiempo adicional" del comando: sale de horas adicionales. Se escribe en el archivo manual.</summary>
    private partial decimal ValorDelTiempoAdicional(decimal horasAdicionales);

    /// <summary>Dato calculado "hay tiempo adicional" del comando: sale de horas adicionales. Se escribe en el archivo manual.</summary>
    private partial bool HayTiempoAdicional(decimal horasAdicionales);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(LiquidarYCobrarLosCargosDelCierre comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. Cargar la raíz.
        var cuentaDelArriendo = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe cuenta del arriendo {comando.NumeroDelArriendo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Liquidar y cobrar los cargos del cierre", cuentaDelArriendo.Estado, EstadoDeLaCuenta.Abierta);

        // 2. Servicios SA que usa, en orden, y los datos calculados (archivo manual) en cuanto están sus datos.
        var calculadoValorDelCombustible = ValorDelCombustible(comando.CombustibleConsumido);
        var calculadoValorDelTiempoAdicional = ValorDelTiempoAdicional(comando.HorasAdicionales);
        var calculadoHayTiempoAdicional = HayTiempoAdicional(comando.HorasAdicionales);
        var respuestaCobrosPorLaPasarelaDePagos1 = cobrosPorLaPasarelaDePagos.Llamar(new CobrosPorLaPasarelaDePagosEntrada(TipoDeOrden.CombustibleConsumido, cuentaDelArriendo.NumeroDelArriendo, calculadoValorDelCombustible, null));
        CobrosPorLaPasarelaDePagosSalida? respuestaCobrosPorLaPasarelaDePagos2 = (calculadoHayTiempoAdicional == true)
            ? cobrosPorLaPasarelaDePagos.Llamar(new CobrosPorLaPasarelaDePagosEntrada(TipoDeOrden.TiempoAdicional, cuentaDelArriendo.NumeroDelArriendo, calculadoValorDelTiempoAdicional, null))
            : null;

        // 4. Reglas del contrato (archivo manual).
        var datos = new LiquidarYCobrarLosCargosDelCierreDatos(comando, cuentaDelArriendo, calculadoValorDelCombustible, calculadoValorDelTiempoAdicional, calculadoHayTiempoAdicional, respuestaCobrosPorLaPasarelaDePagos1, respuestaCobrosPorLaPasarelaDePagos2);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        Entidades.Agregar(cuentaDelArriendo.Cobro, new Cobro(ConceptoDelCobro.CombustibleConsumido, calculadoValorDelCombustible, respuestaCobrosPorLaPasarelaDePagos1.Comprobante, comando.Evidencia));
        if ((calculadoHayTiempoAdicional == true)) Entidades.Agregar(cuentaDelArriendo.Cobro, new Cobro(ConceptoDelCobro.TiempoAdicional, calculadoValorDelTiempoAdicional, (respuestaCobrosPorLaPasarelaDePagos2?.Comprobante ?? throw new DatoFaltante("comprobante del tiempo adicional")), comando.Evidencia));
        repositorio.Guardar(cuentaDelArriendo);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new CargosDelCierreCobrados(cuentaDelArriendo.NumeroDelArriendo, comando.HoraDeRegreso, calculadoValorDelCombustible, calculadoValorDelTiempoAdicional), eventos);
        return new RespuestaDeComando(cuentaDelArriendo.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
