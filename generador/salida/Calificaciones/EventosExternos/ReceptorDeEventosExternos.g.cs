// Generado desde ArchiMate: ApplicationComponent "Contexto Calificaciones" (id-6f29abc193cb4f2fa1234cec80bf0675).
// Capa 3: recibe los eventos de otros contextos y dispara el comando de este contexto
// (eventos_de_otros_contextos del YAML). No editar: el generador reescribe este archivo.
#nullable enable
using System.Text.Json;

namespace YateGear.Calificaciones;

/// <summary>Recibe los eventos de otros contextos. Si un evento tiene junto_con, espera a que lleguen todos
/// los de su grupo (en memoria, por identidad) y entonces dispara el comando con los datos de todos.</summary>
public sealed class ReceptorDeEventosExternos(
    MemoriaDeEventos memoria,
    Bitacora bitacora
)
{
    /// <summary>"Arriendo cerrado" de "Contexto Gestión del arriendo" (id-0f65cc3ebf6649e283d9b634febb03f5). Se recuerda para los comandos que lo requieren.</summary>
    public RespuestaDeEventoExterno Recibir(ArriendoCerrado evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        memoria.Anotar(evento);
        return RespuestaDeEventoExterno.Recordado();
    }

    /// <summary>Lee "Arriendo cerrado" desde JSON y lo recibe. Si falta un dato obligatorio, DatoFaltante (422).</summary>
    public RespuestaDeEventoExterno RecibirArriendoCerrado(JsonElement json) =>
        Recibir(LectorDeEventos.Leer<ArriendoCerrado>(json, ("numeroDelArriendo", "número del arriendo"), ("referenciaAlCRM", "referencia al CRM"), ("propietario", "propietario"), ("fechaYHoraDelCambio", "fecha y hora del cambio")));
}
