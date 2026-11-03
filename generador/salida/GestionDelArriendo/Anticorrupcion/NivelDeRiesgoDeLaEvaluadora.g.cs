// Generado desde ArchiMate: ApplicationService "Nivel de riesgo de la evaluadora" (SA-04, id-b11c0fb607e44ce6ba45736c036e3a0d).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada del servicio SA "Nivel de riesgo de la evaluadora" (SA-04).</summary>
public sealed record NivelDeRiesgoDeLaEvaluadoraEntrada(
    string ReferenciaAlCRM
);

/// <summary>Salida del servicio SA "Nivel de riesgo de la evaluadora" (SA-04).</summary>
public sealed record NivelDeRiesgoDeLaEvaluadoraSalida(
    NivelDeRiesgo Nivel,
    DateOnly Fecha
);

/// <summary>Servicio de la capa anticorrupción "Nivel de riesgo de la evaluadora" (SA-04).</summary>
/// <remarks>
/// <para>Interfaz: "Interfaz con la evaluadora de riesgo" (id-b118a4f717304e4a943e355d2904f1f4).
/// Contraparte: ApplicationComponent "Sistema de la empresa evaluadora de riesgo" (id-29a3f10ca36b4ceda2ed5657d162ef34), sistema externo.</para>
/// <para>Flujos: sale "Datos del cliente autorizados" (id-ca36e9d39f464d0793eb40e0a8370a55); entra "Nivel de riesgo" (id-65e93633762745fe82eb0e5788387816).</para>
/// <para>Contrato de servicio: Nivel de riesgo de la evaluadora (id-d0d598aab81f44e3a9134075d809cf17). Entrada: Datos del cliente autorizados.
/// Salida: Nivel de riesgo y fecha de la evaluación. Reglas: Bajo y medio se traducen a aceptable y alto a no se arrienda (REG-01, V4-SUP-02).</para>
/// </remarks>
public interface INivelDeRiesgoDeLaEvaluadora
{
    /// <summary>Llama al servicio.</summary>
    NivelDeRiesgoDeLaEvaluadoraSalida Llamar(NivelDeRiesgoDeLaEvaluadoraEntrada entrada);
}

/// <summary>"Sistema de la empresa evaluadora de riesgo" simulado: responde con los valores fijos del YAML
/// (casos en orden y, si ninguno se cumple, respuesta_por_defecto).</summary>
public sealed class NivelDeRiesgoDeLaEvaluadoraSimulado(Bitacora bitacora) : INivelDeRiesgoDeLaEvaluadora
{
    /// <inheritdoc />
    public NivelDeRiesgoDeLaEvaluadoraSalida Llamar(NivelDeRiesgoDeLaEvaluadoraEntrada entrada)
    {
        var respuesta =
            (entrada.ReferenciaAlCRM == "CRM-0002") ? new NivelDeRiesgoDeLaEvaluadoraSalida(NivelDeRiesgo.Alto, new DateOnly(2026, 1, 15)) :
            new NivelDeRiesgoDeLaEvaluadoraSalida(NivelDeRiesgo.Medio, new DateOnly(2026, 1, 15));
        bitacora.Anotar("llamada a servicio SA", "Nivel de riesgo de la evaluadora", new { entrada, respuesta });
        return respuesta;
    }
}
