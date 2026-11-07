// Generado desde ArchiMate: ApplicationProcess "Cobrar alquiler y seguro" (SB-13, id-e5737d28667c4b8a9373ac6f62271f96).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en CobrarAlquilerYSeguro.cs.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada del comando "Cobrar alquiler y seguro" (SB-13).</summary>
public sealed record CobrarAlquilerYSeguro(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    string Propietario,
    string ReferenciaAlCRM,
    DateOnly Inicio,
    DateOnly Fin,
    int Dias,
    decimal PrecioPorDia,
    decimal ValorDelSeguro,
    string MedioDePago
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record CobrarAlquilerYSeguroDatos(
    CobrarAlquilerYSeguro Comando,
    decimal ValorDelAlquiler,
    PolizasYReclamosDeLaAseguradoraSalida PolizasYReclamosDeLaAseguradora,
    CobrosPorLaPasarelaDePagosSalida CobrosPorLaPasarelaDePagos1,
    CobrosPorLaPasarelaDePagosSalida CobrosPorLaPasarelaDePagos2
);

/// <summary>Manejador del comando "Cobrar alquiler y seguro" (SB-13).</summary>
/// <remarks>
/// <para>Contrato de servicio: Cobrar alquiler y seguro (id-0630fc686f76430196499d225b64d38a), asociado al servicio de negocio
/// "Cobrar alquiler y seguro" (id-cab68165d54b41639d0bac55d1fd8804), que el comando realiza.</para>
/// <para>Entrada: Arriendo, días, precio por día, valor del seguro y medio de pago del cliente.</para>
/// <para>Salida: Comprobantes del alquiler y del seguro y número de la póliza.</para>
/// <para>Reglas: el contrato no tiene reglas. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class CobrarAlquilerYSeguroManejador(
    Repositorio<CuentaDelArriendo> repositorio,
    BusDeEventos bus,
    IPolizasYReclamosDeLaAseguradora polizasYReclamosDeLaAseguradora,
    ICobrosPorLaPasarelaDePagos cobrosPorLaPasarelaDePagos
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(CobrarAlquilerYSeguroDatos datos);

    /// <summary>Dato calculado "valor del alquiler" del comando: sale de días, precio por día. Se escribe en el archivo manual.</summary>
    private partial decimal ValorDelAlquiler(int dias, decimal precioPorDia);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(CobrarAlquilerYSeguro comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 2. Servicios SA que usa, en orden, y los datos calculados (archivo manual) en cuanto están sus datos.
        var calculadoValorDelAlquiler = ValorDelAlquiler(comando.Dias, comando.PrecioPorDia);
        var respuestaPolizasYReclamosDeLaAseguradora = polizasYReclamosDeLaAseguradora.Llamar(new PolizasYReclamosDeLaAseguradoraEntrada(SolicitudALaAseguradora.Poliza, comando.NumeroDelArriendo, comando.IdentificadorDelYate, comando.ReferenciaAlCRM, comando.Inicio, comando.Fin, null, null, null, null));
        var respuestaCobrosPorLaPasarelaDePagos1 = cobrosPorLaPasarelaDePagos.Llamar(new CobrosPorLaPasarelaDePagosEntrada(TipoDeOrden.Alquiler, comando.NumeroDelArriendo, calculadoValorDelAlquiler, comando.MedioDePago));
        var respuestaCobrosPorLaPasarelaDePagos2 = cobrosPorLaPasarelaDePagos.Llamar(new CobrosPorLaPasarelaDePagosEntrada(TipoDeOrden.Seguro, comando.NumeroDelArriendo, comando.ValorDelSeguro, comando.MedioDePago));

        // 4. Reglas del contrato (archivo manual).
        var datos = new CobrarAlquilerYSeguroDatos(comando, calculadoValorDelAlquiler, respuestaPolizasYReclamosDeLaAseguradora, respuestaCobrosPorLaPasarelaDePagos1, respuestaCobrosPorLaPasarelaDePagos2);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Su identidad se forma con datos;
        //    si ya existe una raíz con esa identidad, 409.
        var cuentaDelArriendo = new CuentaDelArriendo
        {
            Estado = EstadoDeLaCuenta.Abierta,
            IdentificadorDelYate = comando.IdentificadorDelYate,
            Propietario = comando.Propietario,
            PolizaDelArriendo = new PolizaDelArriendo(respuestaPolizasYReclamosDeLaAseguradora.Numero, (respuestaPolizasYReclamosDeLaAseguradora.Valor ?? throw new DatoFaltante("valor"))),
        };
        Entidades.Agregar(cuentaDelArriendo.Cobro, new Cobro(ConceptoDelCobro.Alquiler, calculadoValorDelAlquiler, respuestaCobrosPorLaPasarelaDePagos1.Comprobante, []));
        Entidades.Agregar(cuentaDelArriendo.Cobro, new Cobro(ConceptoDelCobro.Seguro, comando.ValorDelSeguro, respuestaCobrosPorLaPasarelaDePagos2.Comprobante, []));
        repositorio.Agregar(cuentaDelArriendo, $"{(comando.NumeroDelArriendo)}");

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new AlquilerYSeguroCobrados(cuentaDelArriendo.NumeroDelArriendo, respuestaCobrosPorLaPasarelaDePagos1.Comprobante, respuestaCobrosPorLaPasarelaDePagos2.Comprobante), eventos);
        return new RespuestaDeComando(cuentaDelArriendo.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
