// Generado desde ArchiMate: ApplicationComponent "Contexto Operación del arriendo" (id-909c52d6cdf845e6927af4c62d2847fb).
// Capa 3: recibe los eventos de otros contextos y dispara el comando de este contexto
// (eventos_de_otros_contextos del YAML). No editar: el generador reescribe este archivo.
#nullable enable
using System.Text.Json;

namespace YateGear.OperacionDelArriendo;

/// <summary>Recibe los eventos de otros contextos. Si un evento tiene junto_con, espera a que lleguen todos
/// los de su grupo (en memoria, por identidad) y entonces dispara el comando con los datos de todos.</summary>
public sealed class ReceptorDeEventosExternos(
    MemoriaDeEventos memoria,
    Bitacora bitacora
)
{
    /// <summary>"Reserva confirmada" de "Contexto Gestión del arriendo" (id-f7f775aec49c4eb782699183059c6bc2). Se recuerda para los comandos que lo requieren.</summary>
    public RespuestaDeEventoExterno Recibir(ReservaConfirmada evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        memoria.Anotar(evento);
        return RespuestaDeEventoExterno.Recordado();
    }

    /// <summary>Lee "Reserva confirmada" desde JSON y lo recibe. Si falta un dato obligatorio, DatoFaltante (422).</summary>
    public RespuestaDeEventoExterno RecibirReservaConfirmada(JsonElement json) =>
        Recibir(LectorDeEventos.Leer<ReservaConfirmada>(json, ("numeroDelArriendo", "número del arriendo"), ("inicio", "inicio"), ("fin", "fin")));
}
