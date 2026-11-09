// Generado desde ArchiMate: ApplicationService "Avisos y actas de las marinas" (SA-05, id-2754472851d144d5b79323ab235a3f20).
// Capa anticorrupción, lo que sale (G11): lo que la aplicación envía por este servicio SA cuando ocurre un evento del
// contexto (envia del YAML). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Mensaje "Alerta de pérdida de señal" que la aplicación envía por "Avisos y actas de las marinas" cuando ocurre "Pérdida de señal del yate".</summary>
public sealed record AlertaDePerdidaDeSenal(
    string IdentificadorDelYate,
    decimal Latitud,
    decimal Longitud,
    decimal NivelDeCombustible,
    DateTime HoraDeLaLectura
);

/// <summary>Lo que la aplicación envía a "Sistemas de las marinas" por "Avisos y actas de las marinas" (SA-05). No espera respuesta
/// (lenguaje publicado).</summary>
/// <remarks>
/// <para>Interfaz: "Interfaz con las marinas" (id-8e8765a8065440cf8596cf26a6d141b2).
/// Contraparte: ApplicationComponent "Sistemas de las marinas" (id-584b815ed5b5478a8116c2a813a5752b), sistema externo.</para>
/// <para>Flujos: entra "Actas de entrega e inspección" (id-9d498f09a5d849f19ca3878860b49690); sale "Aviso de reserva; alerta de señal" (id-9c54e3f6559e4b3c88d7b8a48da40bc3).</para>
/// <para>Contrato de servicio: Avisos y actas de las marinas (id-b4831a192c314d018432634e6180c468). Entrada: Aviso o alerta para la marina; o acta recibida de la marina.
/// Salida: Constancia de que el aviso llegó; o acta traducida al formato del arriendo. Reglas: Las actas se reciben en el formato que ya usa cada marina, porque las marinas no cambian sus sistemas (MOT-04, INT-MAR).</para>
/// </remarks>
public interface IEmisorDeAvisosYActasDeLasMarinas
{
    /// <summary>Envía "Alerta de pérdida de señal".</summary>
    void Enviar(AlertaDePerdidaDeSenal mensaje);
}

/// <summary>"Sistemas de las marinas" simulado: anota cada envío en la bitácora.</summary>
public sealed class EmisorDeAvisosYActasDeLasMarinasSimulado(Bitacora bitacora) : IEmisorDeAvisosYActasDeLasMarinas
{
    /// <inheritdoc />
    public void Enviar(AlertaDePerdidaDeSenal mensaje) => bitacora.Anotar("envío por servicio SA", "Avisos y actas de las marinas: Alerta de pérdida de señal", mensaje);
}
