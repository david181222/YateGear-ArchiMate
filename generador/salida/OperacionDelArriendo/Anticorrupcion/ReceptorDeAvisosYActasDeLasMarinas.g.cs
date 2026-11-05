// Generado desde ArchiMate: ApplicationService "Avisos y actas de las marinas" (SA-05, id-2754472851d144d5b79323ab235a3f20).
// Capa anticorrupción, lo que entra (G7): lo que el sistema externo le envía a YateGear por este servicio SA
// (recibe del YAML). No editar: el generador reescribe este archivo.
#nullable enable
using System.Text.Json;

namespace YateGear.OperacionDelArriendo;

/// <summary>Mensaje "Acta de entrega recibida" que "Avisos y actas de las marinas" recibe del sistema externo. Dispara "Registrar el acta de entrega".</summary>
public sealed record ActaDeEntregaRecibida(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    List<string> Fotos,
    decimal NivelDeCombustible,
    DateTime HoraDeEntrega,
    string? Observaciones
);

/// <summary>Mensaje "Acta de inspección recibida" que "Avisos y actas de las marinas" recibe del sistema externo. Dispara "Registrar la inspección de devolución".</summary>
public sealed record ActaDeInspeccionRecibida(
    string NumeroDelArriendo,
    List<string> Fotos,
    decimal NivelDeCombustible,
    DateTime HoraDeRegreso,
    List<DanoEncontrado> DanosEncontrados
);

/// <summary>Recibe lo que "Sistemas de las marinas" le envía a YateGear por "Avisos y actas de las marinas" (SA-05)
/// y dispara el comando de cada mensaje, con sus datos por nombre.</summary>
/// <remarks>
/// <para>Contrato de servicio: Avisos y actas de las marinas (id-b4831a192c314d018432634e6180c468). Entrada: Aviso o alerta para la marina; o acta recibida de la marina.</para>
/// <para>Interfaz "Interfaz con las marinas" (id-8e8765a8065440cf8596cf26a6d141b2).</para>
/// </remarks>
public sealed class ReceptorDeAvisosYActasDeLasMarinas(
    Bitacora bitacora,
    RegistrarElActaDeEntregaManejador registrarElActaDeEntrega,
    RegistrarLaInspeccionDeDevolucionManejador registrarLaInspeccionDeDevolucion
)
{
    /// <summary>Lee "Acta de entrega recibida" desde JSON (si falta un dato obligatorio, DatoFaltante: 422) y dispara "Registrar el acta de entrega".</summary>
    public RespuestaDeComando RecibirActaDeEntregaRecibida(JsonElement json)
    {
        var mensaje = LectorDeEventos.Leer<ActaDeEntregaRecibida>(json, ("numeroDelArriendo", "número del arriendo"), ("identificadorDelYate", "identificador del yate"), ("fotos", "fotos"), ("nivelDeCombustible", "nivel de combustible"), ("horaDeEntrega", "hora de entrega"));
        bitacora.Anotar("mensaje recibido", "Avisos y actas de las marinas: Acta de entrega recibida", mensaje);
        return registrarElActaDeEntrega.Manejar(new RegistrarElActaDeEntrega(mensaje.NumeroDelArriendo, mensaje.IdentificadorDelYate, mensaje.Fotos, mensaje.NivelDeCombustible, mensaje.HoraDeEntrega, mensaje.Observaciones));
    }

    /// <summary>Lee "Acta de inspección recibida" desde JSON (si falta un dato obligatorio, DatoFaltante: 422) y dispara "Registrar la inspección de devolución".</summary>
    public RespuestaDeComando RecibirActaDeInspeccionRecibida(JsonElement json)
    {
        var mensaje = LectorDeEventos.Leer<ActaDeInspeccionRecibida>(json, ("numeroDelArriendo", "número del arriendo"), ("fotos", "fotos"), ("nivelDeCombustible", "nivel de combustible"), ("horaDeRegreso", "hora de regreso"), ("danosEncontrados", "daños encontrados"));
        bitacora.Anotar("mensaje recibido", "Avisos y actas de las marinas: Acta de inspección recibida", mensaje);
        return registrarLaInspeccionDeDevolucion.Manejar(new RegistrarLaInspeccionDeDevolucion(mensaje.NumeroDelArriendo, mensaje.Fotos, mensaje.NivelDeCombustible, mensaje.HoraDeRegreso, mensaje.DanosEncontrados));
    }
}
