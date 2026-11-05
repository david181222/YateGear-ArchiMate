// Generado desde ArchiMate: ApplicationComponent "Contexto Disponibilidad de yates" (id-0d93d731f6fd4b21acbf20d3cb28cf6f).
// Capa 3: recibe los eventos de otros contextos y dispara el comando de este contexto
// (eventos_de_otros_contextos del YAML). No editar: el generador reescribe este archivo.
#nullable enable
using System.Text.Json;

namespace YateGear.DisponibilidadDeYates;

/// <summary>Recibe los eventos de otros contextos. Si un evento tiene junto_con, espera a que lleguen todos
/// los de su grupo (en memoria, por identidad) y entonces dispara el comando con los datos de todos.</summary>
public sealed class ReceptorDeEventosExternos(
    Bitacora bitacora,
    GestionarLaOcupacionDelCalendarioManejador gestionarLaOcupacionDelCalendario
)
{
    /// <summary>"Arriendo no realizado por riesgo alto" de "Contexto Gestión del arriendo" (id-bb4b23b9412742f89ac3ae34504a8391). Dispara "Gestionar la ocupación del calendario".</summary>
    public RespuestaDeEventoExterno Recibir(ArriendoNoRealizadoPorRiesgoAlto evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        return RespuestaDeEventoExterno.Ejecutado(gestionarLaOcupacionDelCalendario.Manejar(new GestionarLaOcupacionDelCalendario(evento.IdentificadorDelYate, evento.Inicio, evento.Fin, evento.NumeroDelArriendo, AccionSobreLaOcupacion.Soltar)));
    }

    /// <summary>Lee "Arriendo no realizado por riesgo alto" desde JSON y lo recibe. Si falta un dato obligatorio, DatoFaltante (422).</summary>
    public RespuestaDeEventoExterno RecibirArriendoNoRealizadoPorRiesgoAlto(JsonElement json) =>
        Recibir(LectorDeEventos.Leer<ArriendoNoRealizadoPorRiesgoAlto>(json, ("numeroDelArriendo", "número del arriendo"), ("identificadorDelYate", "identificador del yate"), ("inicio", "inicio"), ("fin", "fin")));

    /// <summary>"Reserva cancelada" de "Contexto Gestión del arriendo" (id-28e06fd82a7641228d89ded443509b64). Dispara "Gestionar la ocupación del calendario".</summary>
    public RespuestaDeEventoExterno Recibir(ReservaCancelada evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        return RespuestaDeEventoExterno.Ejecutado(gestionarLaOcupacionDelCalendario.Manejar(new GestionarLaOcupacionDelCalendario(evento.IdentificadorDelYate, evento.Inicio, evento.Fin, evento.NumeroDelArriendo, AccionSobreLaOcupacion.Soltar)));
    }

    /// <summary>Lee "Reserva cancelada" desde JSON y lo recibe. Si falta un dato obligatorio, DatoFaltante (422).</summary>
    public RespuestaDeEventoExterno RecibirReservaCancelada(JsonElement json) =>
        Recibir(LectorDeEventos.Leer<ReservaCancelada>(json, ("numeroDelArriendo", "número del arriendo"), ("identificadorDelYate", "identificador del yate"), ("inicio", "inicio"), ("fin", "fin")));

    /// <summary>"Reserva confirmada" de "Contexto Gestión del arriendo" (id-f7f775aec49c4eb782699183059c6bc2). Dispara "Gestionar la ocupación del calendario".</summary>
    public RespuestaDeEventoExterno Recibir(ReservaConfirmada evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        return RespuestaDeEventoExterno.Ejecutado(gestionarLaOcupacionDelCalendario.Manejar(new GestionarLaOcupacionDelCalendario(evento.IdentificadorDelYate, evento.Inicio, evento.Fin, evento.NumeroDelArriendo, AccionSobreLaOcupacion.Ocupar)));
    }

    /// <summary>Lee "Reserva confirmada" desde JSON y lo recibe. Si falta un dato obligatorio, DatoFaltante (422).</summary>
    public RespuestaDeEventoExterno RecibirReservaConfirmada(JsonElement json) =>
        Recibir(LectorDeEventos.Leer<ReservaConfirmada>(json, ("numeroDelArriendo", "número del arriendo"), ("identificadorDelYate", "identificador del yate"), ("inicio", "inicio"), ("fin", "fin")));

    /// <summary>"Reserva solicitada" de "Contexto Gestión del arriendo" (id-ba01aa1a0874474086ba64badf2991e3). Dispara "Gestionar la ocupación del calendario".</summary>
    public RespuestaDeEventoExterno Recibir(ReservaSolicitada evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        return RespuestaDeEventoExterno.Ejecutado(gestionarLaOcupacionDelCalendario.Manejar(new GestionarLaOcupacionDelCalendario(evento.IdentificadorDelYate, evento.Inicio, evento.Fin, evento.NumeroDelArriendo, AccionSobreLaOcupacion.Apartar)));
    }

    /// <summary>Lee "Reserva solicitada" desde JSON y lo recibe. Si falta un dato obligatorio, DatoFaltante (422).</summary>
    public RespuestaDeEventoExterno RecibirReservaSolicitada(JsonElement json) =>
        Recibir(LectorDeEventos.Leer<ReservaSolicitada>(json, ("numeroDelArriendo", "número del arriendo"), ("identificadorDelYate", "identificador del yate"), ("inicio", "inicio"), ("fin", "fin")));
}
