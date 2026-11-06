// Generado desde ArchiMate: ApplicationComponent "Contexto Calificaciones" (id-6f29abc193cb4f2fa1234cec80bf0675).
// Políticas del contexto: un evento dispara un comando del mismo contexto (relación de disparo del modelo).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.Calificaciones;

/// <summary>Suscribe en el bus las políticas internas del contexto.</summary>
public static class Politicas
{
    /// <summary>Registra cada política.</summary>
    public static void Registrar(IServiceProvider servicios)
    {
        var bus = servicios.GetRequiredService<BusDeEventos>();
    }
}
