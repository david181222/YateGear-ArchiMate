// Generado desde ArchiMate: ApplicationComponent "Contexto Disponibilidad de yates" (id-0d93d731f6fd4b21acbf20d3cb28cf6f).
// Políticas del contexto: un evento dispara un comando del mismo contexto (relación de disparo del modelo).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Suscribe en el bus las políticas internas del contexto.</summary>
public static class Politicas
{
    /// <summary>Registra cada política.</summary>
    public static void Registrar(IServiceProvider servicios)
    {
        var bus = servicios.GetRequiredService<BusDeEventos>();
    }
}
