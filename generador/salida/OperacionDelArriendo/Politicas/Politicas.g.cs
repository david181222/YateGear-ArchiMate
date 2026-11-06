// Generado desde ArchiMate: ApplicationComponent "Contexto Operación del arriendo" (id-909c52d6cdf845e6927af4c62d2847fb).
// Políticas del contexto: un evento dispara un comando del mismo contexto (relación de disparo del modelo).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Suscribe en el bus las políticas internas del contexto.</summary>
public static class Politicas
{
    /// <summary>Registra cada política.</summary>
    public static void Registrar(IServiceProvider servicios)
    {
        var bus = servicios.GetRequiredService<BusDeEventos>();

        // "Inspección de devolución registrada" dispara "Determinar las diferencias entre entrega y devolución" (relación id-653c0c10e4184badb60b3efcc37e9720).
        bus.Suscribir<InspeccionDeDevolucionRegistrada>(e => servicios.GetRequiredService<DeterminarLasDiferenciasEntreEntregaYDevolucionManejador>()
            .Manejar(new DeterminarLasDiferenciasEntreEntregaYDevolucion(e.NumeroDelArriendo)));
    }
}
