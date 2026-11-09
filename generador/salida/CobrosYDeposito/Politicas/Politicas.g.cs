// Generado desde ArchiMate: ApplicationComponent "Contexto Cobros y depósito" (id-859686865fd4465397859188d62c971c).
// Políticas del contexto: un evento dispara un comando del mismo contexto (relación de disparo del modelo).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Suscribe en el bus las políticas internas del contexto.</summary>
public static class Politicas
{
    /// <summary>Registra cada política.</summary>
    public static void Registrar(IServiceProvider servicios)
    {
        var bus = servicios.GetRequiredService<BusDeEventos>();

        // "Daños descontados del depósito" dispara "Reclamar el excedente de daños a la aseguradora" (relación id-d7326593785343188e965d066cc88e7c), solo si se cumple su condición.
        bus.Suscribir<DanosDescontadosDelDeposito>(e =>
        {
            if (!(e.ValorQueExcedeElDeposito == 0m))
            {
                servicios.GetRequiredService<ReclamarElExcedenteDeDanosALaAseguradoraManejador>().Manejar(new ReclamarElExcedenteDeDanosALaAseguradora(e.NumeroDelArriendo, e.ValorDeLosDanos, e.ValorDescontadoDelDeposito, e.ValorQueExcedeElDeposito, e.Evidencia));
            }
        });

        // Varios eventos disparan "Cerrar las cuentas del arriendo" (G10, D7): Cargos del cierre cobrados, Depósito liberado, Daños descontados del depósito.
        bus.Suscribir<CargosDelCierreCobrados>(e => CerrarLasCuentasDelArriendoPorVariosEventos(servicios, e));          // relación id-67a09166f3204429b95b9d101765aff0
        bus.Suscribir<DepositoLiberado>(e => CerrarLasCuentasDelArriendoPorVariosEventos(servicios, e));          // relación id-8cd447d97bbc4c52a4e6468f6ce1bcba
        bus.Suscribir<DanosDescontadosDelDeposito>(e => CerrarLasCuentasDelArriendoPorVariosEventos(servicios, e));          // relación id-f5e26d2cf86a4a72a9f3cdf4945855ff

        // "Cuenta del arriendo cerrada": "Envío de arriendos cerrados a Finanzas" envía "Arriendo cerrado para Finanzas" (lenguaje publicado, G11).
        bus.Suscribir<CuentaDelArriendoCerrada>(e => servicios.GetRequiredService<IEmisorDeEnvioDeArriendosCerradosAFinanzas>()
            .Enviar(new ArriendoCerradoParaFinanzas(e.NumeroDelArriendo, e.Propietario, e.IdentificadorDelYate, e.ValorDelAlquiler, e.Comision, e.ValorDelPropietario)));
    }

    /// <summary>"Cerrar las cuentas del arriendo" corre cuando llegaron, para la misma identidad, todos estos eventos: "Cargos del cierre cobrados" y uno de estos: "Depósito liberado", "Daños descontados del depósito".</summary>
    private static void CerrarLasCuentasDelArriendoPorVariosEventos(IServiceProvider servicios, IEvento e)
    {
        var juntos = servicios.GetRequiredService<EsperaDeEventos>().Anotar("política: Cerrar las cuentas del arriendo", ["Cargos del cierre cobrados"], e, out _,
            ["Depósito liberado", "Daños descontados del depósito"]);
        if (juntos is null)
        {
            return;
        }
        var cargosDelCierreCobrados = (CargosDelCierreCobrados)juntos["Cargos del cierre cobrados"];
        var depositoLiberado = juntos.GetValueOrDefault("Depósito liberado") as DepositoLiberado;
        var danosDescontadosDelDeposito = juntos.GetValueOrDefault("Daños descontados del depósito") as DanosDescontadosDelDeposito;
        servicios.GetRequiredService<CerrarLasCuentasDelArriendoManejador>().Manejar(new CerrarLasCuentasDelArriendo(e.Identidad, cargosDelCierreCobrados.HoraDeRegreso, (depositoLiberado is not null ? DecisionSobreElDeposito.Liberado : (danosDescontadosDelDeposito is not null ? DecisionSobreElDeposito.Descontado : null))));
    }
}
