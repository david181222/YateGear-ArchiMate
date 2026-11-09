// Generado desde ArchiMate: ApplicationService "Consultar el estado de cuenta del arriendo" (SB-18, id-e093f7b040c243449523e515011813d0).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en ConsultarElEstadoDeCuentaDelArriendo.cs.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Entrada de la consulta "Consultar el estado de cuenta del arriendo" (SB-18).</summary>
public sealed record ConsultarElEstadoDeCuentaDelArriendo(
    string NumeroDelArriendo
);

/// <summary>Salida de la consulta "Consultar el estado de cuenta del arriendo".</summary>
public sealed record ConsultarElEstadoDeCuentaDelArriendoSalida(
    EstadoDeLaCuenta Estado,
    decimal? Comision,
    decimal? ValorDelPropietario,
    decimal? ValorDelDeposito,
    List<string>? EvidenciaDelDescuento,
    List<Cobro> Movimientos,
    EstadoDelDeposito? EstadoDelDeposito
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: la consulta y la raíz; y las demás raíces que lee, con la misma identidad (null si no existen).</summary>
public sealed record ConsultarElEstadoDeCuentaDelArriendoDatos(ConsultarElEstadoDeCuentaDelArriendo Consulta, CuentaDelArriendo CuentaDelArriendo, DepositoParaDanos? DepositoParaDanos);

/// <summary>Manejador de la consulta "Consultar el estado de cuenta del arriendo" (SB-18). No cambia la raíz.</summary>
/// <remarks>
/// <para>Contrato de servicio: Consultar el estado de cuenta del arriendo (id-351bf3719c344a159d64e004c3eab7df), asociado al servicio de negocio
/// "Consultar el estado de cuenta del arriendo" (id-6451adac6a3a47c58968469b72feb93c).</para>
/// <para>Entrada: Número de arriendo.</para>
/// <para>Salida: Lista de movimientos con fecha, concepto, valor y evidencia.</para>
/// <para>Reglas: Se rechaza si quien consulta no es el cliente del arriendo ni un empleado de YateGear, porque son datos de pago (Ley 1581, H-19). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class ConsultarElEstadoDeCuentaDelArriendoManejador(Repositorio<CuentaDelArriendo> repositorio, Repositorio<DepositoParaDanos> repositorioDepositoParaDanos)
{
    /// <summary>Reglas del contrato. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(ConsultarElEstadoDeCuentaDelArriendoDatos datos);

    /// <summary>Dato calculado "movimientos". Se escribe en el archivo manual.</summary>
    private partial List<Cobro> Movimientos(ConsultarElEstadoDeCuentaDelArriendoDatos datos);

    /// <summary>Dato calculado "estado del depósito". Se escribe en el archivo manual.</summary>
    private partial EstadoDelDeposito? EstadoDelDeposito(ConsultarElEstadoDeCuentaDelArriendoDatos datos);

    /// <summary>Ejecuta la consulta.</summary>
    public ConsultarElEstadoDeCuentaDelArriendoSalida Manejar(ConsultarElEstadoDeCuentaDelArriendo consulta)
    {
        var cuentaDelArriendo = repositorio.Obtener(consulta.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe cuenta del arriendo {consulta.NumeroDelArriendo}.");
        var depositoParaDanos = repositorioDepositoParaDanos.Obtener(consulta.NumeroDelArriendo);
        var datos = new ConsultarElEstadoDeCuentaDelArriendoDatos(consulta, cuentaDelArriendo, depositoParaDanos);
        ValidarReglas(datos);
        return new ConsultarElEstadoDeCuentaDelArriendoSalida(
            cuentaDelArriendo.Estado,
            cuentaDelArriendo.Comision,
            cuentaDelArriendo.ValorDelPropietario,
            depositoParaDanos?.ValorDelDeposito,
            depositoParaDanos?.EvidenciaDelDescuento,
            Movimientos(datos),
            EstadoDelDeposito(datos)
        );
    }
}
