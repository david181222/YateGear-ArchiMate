// Generado desde ArchiMate: ApplicationService "Avisos y actas de las marinas" (SA-05, id-2754472851d144d5b79323ab235a3f20).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada del servicio SA "Avisos y actas de las marinas" (SA-05).</summary>
public sealed record AvisosYActasDeLasMarinasEntrada(
    string IdentificadorDelYate,
    string Marina,
    DateOnly Inicio,
    DateOnly Fin,
    string ReferenciaAlCRM
);

/// <summary>Salida del servicio SA "Avisos y actas de las marinas" (SA-05).</summary>
public sealed record AvisosYActasDeLasMarinasSalida(
    string ConstanciaDelAviso
);

/// <summary>Servicio de la capa anticorrupción "Avisos y actas de las marinas" (SA-05).</summary>
/// <remarks>
/// <para>Interfaz: "Interfaz con las marinas" (id-8e8765a8065440cf8596cf26a6d141b2).
/// Contraparte: ApplicationComponent "Sistemas de las marinas" (id-584b815ed5b5478a8116c2a813a5752b), sistema externo.</para>
/// <para>Flujos: entra "Actas de entrega e inspección" (id-9d498f09a5d849f19ca3878860b49690); sale "Aviso de reserva; alerta de señal" (id-9c54e3f6559e4b3c88d7b8a48da40bc3).</para>
/// <para>Contrato de servicio: Avisos y actas de las marinas (id-b4831a192c314d018432634e6180c468). Entrada: Aviso o alerta para la marina; o acta recibida de la marina.
/// Salida: Constancia de que el aviso llegó; o acta traducida al formato del arriendo. Reglas: Las actas se reciben en el formato que ya usa cada marina, porque las marinas no cambian sus sistemas (MOT-04, INT-MAR).</para>
/// </remarks>
public interface IAvisosYActasDeLasMarinas
{
    /// <summary>Llama al servicio.</summary>
    AvisosYActasDeLasMarinasSalida Llamar(AvisosYActasDeLasMarinasEntrada entrada);
}

/// <summary>"Sistemas de las marinas" simulado: responde con los valores fijos del YAML
/// (casos en orden y, si ninguno se cumple, respuesta_por_defecto).</summary>
public sealed class AvisosYActasDeLasMarinasSimulado(Bitacora bitacora) : IAvisosYActasDeLasMarinas
{
    /// <inheritdoc />
    public AvisosYActasDeLasMarinasSalida Llamar(AvisosYActasDeLasMarinasEntrada entrada)
    {
        var respuesta =
            new AvisosYActasDeLasMarinasSalida("AVISO-RECIBIDO");
        bitacora.Anotar("llamada a servicio SA", "Avisos y actas de las marinas", new { entrada, respuesta });
        return respuesta;
    }
}
