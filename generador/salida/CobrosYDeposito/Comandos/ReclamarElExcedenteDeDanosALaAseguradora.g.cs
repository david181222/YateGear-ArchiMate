// Generado desde ArchiMate: ApplicationProcess "Reclamar el excedente de daños a la aseguradora" (SB-16, id-afb038030e754dd490f69fcbf6a446e0).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en ReclamarElExcedenteDeDanosALaAseguradora.cs.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada del comando "Reclamar el excedente de daños a la aseguradora" (SB-16).</summary>
public sealed record ReclamarElExcedenteDeDanosALaAseguradora(
    string NumeroDelArriendo,
    decimal ValorDeLosDanos,
    decimal ValorDescontadoDelDeposito,
    decimal ValorQueExcedeElDeposito,
    List<string> Evidencia
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record ReclamarElExcedenteDeDanosALaAseguradoraDatos(
    ReclamarElExcedenteDeDanosALaAseguradora Comando,
    CuentaDelArriendo CuentaDelArriendo,
    string NumeroDePoliza,
    PolizasYReclamosDeLaAseguradoraSalida PolizasYReclamosDeLaAseguradora
);

/// <summary>Manejador del comando "Reclamar el excedente de daños a la aseguradora" (SB-16).</summary>
/// <remarks>
/// <para>Contrato de servicio: Reclamar el excedente de daños a la aseguradora (id-68d91d580faf4234a20279768c8520e6), asociado al servicio de negocio
/// "Reclamar el excedente de daños a la aseguradora" (id-575ab794c65743f590489b86ba736dcb), que el comando realiza.</para>
/// <para>Entrada: Arriendo, número de póliza, valor de los daños, valor descontado del depósito y evidencia.</para>
/// <para>Salida: Reclamo enviado con su número y, cuando llegue, la respuesta de la aseguradora.</para>
/// <para>Reglas: Se rechaza si el daño no supera el depósito (REG-01) o si falta la evidencia de la entrega y de la inspección (EXC-02). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class ReclamarElExcedenteDeDanosALaAseguradoraManejador(
    Repositorio<ReclamoALaAseguradora> repositorio,
    BusDeEventos bus,
    Repositorio<CuentaDelArriendo> repositorioCuentaDelArriendo,
    IPolizasYReclamosDeLaAseguradora polizasYReclamosDeLaAseguradora
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(ReclamarElExcedenteDeDanosALaAseguradoraDatos datos);

    /// <summary>Dato calculado "número de póliza" del comando: sale de Cuenta del arriendo. Se escribe en el archivo manual.</summary>
    private partial string NumeroDePoliza(CuentaDelArriendo cuentaDelArriendo);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(ReclamarElExcedenteDeDanosALaAseguradora comando)
    {
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 1d. Otras raíces que el comando lee (G6), por el dato con el nombre de su identidad; 404 si no existen.
        var cuentaDelArriendo = repositorioCuentaDelArriendo.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe cuenta del arriendo {comando.NumeroDelArriendo}.");

        // 2. Servicios SA que usa, en orden, y los datos calculados (archivo manual) en cuanto están sus datos.
        var calculadoNumeroDePoliza = NumeroDePoliza(cuentaDelArriendo);
        var respuestaPolizasYReclamosDeLaAseguradora = polizasYReclamosDeLaAseguradora.Llamar(new PolizasYReclamosDeLaAseguradoraEntrada(SolicitudALaAseguradora.Reclamo, comando.NumeroDelArriendo, null, null, null, null, calculadoNumeroDePoliza, comando.ValorDeLosDanos, comando.ValorDescontadoDelDeposito, comando.Evidencia));

        // 4. Reglas del contrato declaradas en el YAML (reglas), en orden.
        if ((comando.ValorQueExcedeElDeposito <= 0m))
        {
            throw new ReglaIncumplida("REG-01", "El daño no supera el depósito: no hay nada que reclamar a la aseguradora.");
        }
        if (comando.Evidencia is not { Count: > 0 })
        {
            throw new ReglaIncumplida("EXC-02", "Falta la evidencia de la entrega y de la inspección.");
        }

        // 4b. Las demás reglas del contrato (archivo manual).
        var datos = new ReclamarElExcedenteDeDanosALaAseguradoraDatos(comando, cuentaDelArriendo, calculadoNumeroDePoliza, respuestaPolizasYReclamosDeLaAseguradora);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Al guardarla recibe su identidad.
        var reclamoALaAseguradora = new ReclamoALaAseguradora
        {
            Estado = EstadoDelReclamo.Enviado,
            IdentificadorDelArriendo = comando.NumeroDelArriendo,
            NumeroDePoliza = calculadoNumeroDePoliza,
            ValorDeLosDanos = comando.ValorDeLosDanos,
            ValorDescontadoDelDeposito = comando.ValorDescontadoDelDeposito,
            Evidencia = comando.Evidencia,
        };
        repositorio.Guardar(reclamoALaAseguradora);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new ReclamoEnviadoALaAseguradora(reclamoALaAseguradora.NumeroDeReclamo, reclamoALaAseguradora.IdentificadorDelArriendo, comando.ValorQueExcedeElDeposito, respuestaPolizasYReclamosDeLaAseguradora.Numero, respuestaPolizasYReclamosDeLaAseguradora.EstadoDelReclamo), eventos);
        return new RespuestaDeComando(reclamoALaAseguradora.NumeroDeReclamo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
