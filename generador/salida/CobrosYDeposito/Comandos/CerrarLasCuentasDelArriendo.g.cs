// Generado desde ArchiMate: ApplicationProcess "Cerrar las cuentas del arriendo" (SB-17, id-5ef920b9e381405495dbdfe1877eb75b).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en CerrarLasCuentasDelArriendo.cs.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada del comando "Cerrar las cuentas del arriendo" (SB-17).</summary>
public sealed record CerrarLasCuentasDelArriendo(
    string NumeroDelArriendo,
    DateTime HoraDelCierre,
    DecisionSobreElDeposito? DecisionSobreElDeposito
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record CerrarLasCuentasDelArriendoDatos(
    CerrarLasCuentasDelArriendo Comando,
    CuentaDelArriendo CuentaDelArriendo,
    decimal ValorDelAlquiler,
    decimal Comision,
    decimal ValorDelPropietario
);

/// <summary>Manejador del comando "Cerrar las cuentas del arriendo" (SB-17).</summary>
/// <remarks>
/// <para>Contrato de servicio: Cerrar las cuentas del arriendo (id-4cf062b2782044669f3d49e65f16d93b), asociado al servicio de negocio
/// "Cerrar las cuentas del arriendo" (id-a6ff0409f0a743e3b484891c75b53bb8), que el comando realiza.</para>
/// <para>Entrada: Arriendo devuelto, sus cobros y la decisión sobre el depósito.</para>
/// <para>Salida: Cuentas cerradas con el valor del alquiler, la comisión y el valor del propietario, enviados a Finanzas.</para>
/// <para>Reglas: Se rechaza mientras falte un cargo del cierre o la decisión sobre el depósito, porque con los ajustes se cierra el arriendo (E2E-01). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class CerrarLasCuentasDelArriendoManejador(
    Repositorio<CuentaDelArriendo> repositorio,
    BusDeEventos bus
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(CerrarLasCuentasDelArriendoDatos datos);

    /// <summary>Dato calculado "valor del alquiler" del comando: sale de Cuenta del arriendo. Se escribe en el archivo manual.</summary>
    private partial decimal ValorDelAlquiler(CuentaDelArriendo cuentaDelArriendo);

    /// <summary>Dato calculado "comisión" del comando: sale de valor del alquiler. Se escribe en el archivo manual.</summary>
    private partial decimal Comision(decimal valorDelAlquiler);

    /// <summary>Dato calculado "valor del propietario" del comando: sale de valor del alquiler, comisión. Se escribe en el archivo manual.</summary>
    private partial decimal ValorDelPropietario(decimal valorDelAlquiler, decimal comision);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(CerrarLasCuentasDelArriendo comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. Cargar la raíz.
        var cuentaDelArriendo = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe cuenta del arriendo {comando.NumeroDelArriendo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Cerrar las cuentas del arriendo", cuentaDelArriendo.Estado, EstadoDeLaCuenta.Abierta);

        // 2. Servicios SA que usa, en orden, y los datos calculados (archivo manual) en cuanto están sus datos.
        var calculadoValorDelAlquiler = ValorDelAlquiler(cuentaDelArriendo);
        var calculadoComision = Comision(calculadoValorDelAlquiler);
        var calculadoValorDelPropietario = ValorDelPropietario(calculadoValorDelAlquiler, calculadoComision);

        // 4. Reglas del contrato (archivo manual).
        var datos = new CerrarLasCuentasDelArriendoDatos(comando, cuentaDelArriendo, calculadoValorDelAlquiler, calculadoComision, calculadoValorDelPropietario);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        cuentaDelArriendo.Comision = calculadoComision;
        cuentaDelArriendo.ValorDelPropietario = calculadoValorDelPropietario;
        cuentaDelArriendo.Estado = EstadoDeLaCuenta.Cerrada;
        repositorio.Guardar(cuentaDelArriendo);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new CuentaDelArriendoCerrada(cuentaDelArriendo.NumeroDelArriendo, comando.HoraDelCierre, cuentaDelArriendo.IdentificadorDelYate, cuentaDelArriendo.Propietario, calculadoValorDelAlquiler, calculadoComision, calculadoValorDelPropietario), eventos);
        return new RespuestaDeComando(cuentaDelArriendo.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
