// Generado desde ArchiMate: ApplicationProcess "Reembolsar una cancelación" (SB-15, id-599456d5ca8f45b0b82efa9a05b254d2).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en ReembolsarUnaCancelacion.cs.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada del comando "Reembolsar una cancelación" (SB-15).</summary>
public sealed record ReembolsarUnaCancelacion(
    string NumeroDelArriendo,
    int DiasDeAnticipacion
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record ReembolsarUnaCancelacionDatos(
    ReembolsarUnaCancelacion Comando,
    CuentaDelArriendo CuentaDelArriendo,
    decimal ValorDelReembolso,
    ContratosConPropietariosYClientesSalida ContratosConPropietariosYClientes,
    bool Reembolsable,
    CobrosPorLaPasarelaDePagosSalida? CobrosPorLaPasarelaDePagos,
    ReembolsarUnaCancelacionResultado Resultado
);

/// <summary>Resultados de "Reembolsar una cancelación": un evento por resultado.</summary>
public enum ReembolsarUnaCancelacionResultado
{
    /// <summary>Publica "Cancelación reembolsada".</summary>
    CancelacionReembolsada,
    /// <summary>Publica "Cancelación no reembolsada".</summary>
    CancelacionNoReembolsada,
}

/// <summary>Manejador del comando "Reembolsar una cancelación" (SB-15).</summary>
/// <remarks>
/// <para>Contrato de servicio: Reembolsar una cancelación (id-3e6363728e104f31a5d3a2104e66869c), asociado al servicio de negocio
/// "Reembolsar una cancelación" (id-80cb6926115e4a27b31732ba32d21612), que el comando realiza.</para>
/// <para>Entrada: Arriendo cancelado, días de anticipación y condiciones de cancelación del contrato con el cliente.</para>
/// <para>Salida: Valor devuelto con su comprobante, o la razón por la que no hay devolución.</para>
/// <para>Reglas: No se reembolsa la cancelación hecha muy cerca de la fecha; el plazo lo fija el contrato con el cliente (EXC-02, D-03). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class ReembolsarUnaCancelacionManejador(
    Repositorio<CuentaDelArriendo> repositorio,
    BusDeEventos bus,
    IContratosConPropietariosYClientes contratosConPropietariosYClientes,
    ICobrosPorLaPasarelaDePagos cobrosPorLaPasarelaDePagos
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(ReembolsarUnaCancelacionDatos datos);

    /// <summary>Dato calculado "valor del reembolso" del comando: sale de Cuenta del arriendo. Se escribe en el archivo manual.</summary>
    private partial decimal ValorDelReembolso(CuentaDelArriendo cuentaDelArriendo);

    /// <summary>Dato calculado "reembolsable" del comando: sale de días de anticipación, días mínimos para el reembolso. Se escribe en el archivo manual.</summary>
    private partial bool Reembolsable(int diasDeAnticipacion, int diasMinimosParaElReembolso);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(ReembolsarUnaCancelacion comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. Cargar la raíz.
        var cuentaDelArriendo = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe cuenta del arriendo {comando.NumeroDelArriendo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Reembolsar una cancelación", cuentaDelArriendo.Estado, EstadoDeLaCuenta.Abierta);

        // 2. Servicios SA que usa, en orden, y los datos calculados (archivo manual) en cuanto están sus datos.
        var calculadoValorDelReembolso = ValorDelReembolso(cuentaDelArriendo);
        var respuestaContratosConPropietariosYClientes = contratosConPropietariosYClientes.Llamar(new ContratosConPropietariosYClientesEntrada(cuentaDelArriendo.NumeroDelArriendo));
        var calculadoReembolsable = Reembolsable(comando.DiasDeAnticipacion, respuestaContratosConPropietariosYClientes.DiasMinimosParaElReembolso);
        CobrosPorLaPasarelaDePagosSalida? respuestaCobrosPorLaPasarelaDePagos = (calculadoReembolsable == true)
            ? cobrosPorLaPasarelaDePagos.Llamar(new CobrosPorLaPasarelaDePagosEntrada(TipoDeOrden.Reembolso, cuentaDelArriendo.NumeroDelArriendo, calculadoValorDelReembolso, null))
            : null;

        // 3. Elegir el resultado (condición si del YAML).
        var resultado =
            (calculadoReembolsable == true) ? ReembolsarUnaCancelacionResultado.CancelacionReembolsada :
            (calculadoReembolsable == false) ? ReembolsarUnaCancelacionResultado.CancelacionNoReembolsada :
            throw new ReglaIncumplida("resultados", "Ningún resultado de \"Reembolsar una cancelación\" se cumple con estos datos.");

        // 4. Reglas del contrato declaradas en el YAML (reglas), en orden.
        if ((respuestaCobrosPorLaPasarelaDePagos?.Aprobada == false))
        {
            throw new ReglaIncumplida("INT-PAG", "La pasarela no aprobó el reembolso.");
        }

        // 4b. Las demás reglas del contrato (archivo manual).
        var datos = new ReembolsarUnaCancelacionDatos(comando, cuentaDelArriendo, calculadoValorDelReembolso, respuestaContratosConPropietariosYClientes, calculadoReembolsable, respuestaCobrosPorLaPasarelaDePagos, resultado);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        switch (resultado)
        {
            case ReembolsarUnaCancelacionResultado.CancelacionReembolsada:
                Entidades.Agregar(cuentaDelArriendo.Cobro, new Cobro(ConceptoDelCobro.Reembolso, calculadoValorDelReembolso, (respuestaCobrosPorLaPasarelaDePagos?.Comprobante ?? throw new DatoFaltante("comprobante del reembolso")), [], (respuestaCobrosPorLaPasarelaDePagos?.FechaDeLaOrden ?? throw new DatoFaltante("fecha del reembolso"))));
                break;
        }
        switch (resultado)
        {
            case ReembolsarUnaCancelacionResultado.CancelacionReembolsada:
                cuentaDelArriendo.Estado = EstadoDeLaCuenta.Cerrada;
                break;
            case ReembolsarUnaCancelacionResultado.CancelacionNoReembolsada:
                cuentaDelArriendo.Estado = EstadoDeLaCuenta.Cerrada;
                break;
        }
        repositorio.Guardar(cuentaDelArriendo);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        switch (resultado)
        {
            case ReembolsarUnaCancelacionResultado.CancelacionReembolsada:
                Publicar(new CancelacionReembolsada(cuentaDelArriendo.NumeroDelArriendo, calculadoValorDelReembolso, (respuestaCobrosPorLaPasarelaDePagos?.Comprobante ?? throw new DatoFaltante("comprobante del reembolso"))), eventos);
                break;
            case ReembolsarUnaCancelacionResultado.CancelacionNoReembolsada:
                Publicar(new CancelacionNoReembolsada(cuentaDelArriendo.NumeroDelArriendo, comando.DiasDeAnticipacion, respuestaContratosConPropietariosYClientes.DiasMinimosParaElReembolso), eventos);
                break;
        }
        return new RespuestaDeComando(cuentaDelArriendo.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
