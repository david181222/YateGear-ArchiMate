// Generado desde ArchiMate: ApplicationComponent "Contexto Gestión del arriendo" (id-fdcc9b19f08a492f8ccd5dd4559926bc).
// Capa 3: recibe los eventos de otros contextos y dispara el comando de este contexto
// (eventos_de_otros_contextos del YAML). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Recibe los eventos de otros contextos. Si un evento tiene junto_con, espera a que lleguen todos
/// los de su grupo (en memoria, por identidad) y entonces dispara el comando con los datos de todos.</summary>
public sealed class ReceptorDeEventosExternos(
    EsperaDeEventos espera,
    Bitacora bitacora,
    ConfirmarLaReservaManejador confirmarLaReserva,
    RegistrarElAvanceDelArriendoManejador registrarElAvanceDelArriendo
)
{
    /// <summary>"Alquiler y seguro cobrados" de "Contexto Cobros y depósito" (id-a5729d322f444202bc1a34c7d68a46d8). Dispara "Confirmar la reserva" junto con Depósito bloqueado.</summary>
    public RespuestaDeEventoExterno Recibir(AlquilerYSeguroCobrados evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        var juntos = espera.Anotar("Confirmar la reserva", ["Alquiler y seguro cobrados", "Depósito bloqueado"], evento, out var faltan);
        if (juntos is null)
        {
            return RespuestaDeEventoExterno.Esperando(faltan);
        }
        var alquilerYSeguroCobrados = (AlquilerYSeguroCobrados)juntos["Alquiler y seguro cobrados"];
        var depositoBloqueado = (DepositoBloqueado)juntos["Depósito bloqueado"];
        return RespuestaDeEventoExterno.Ejecutado(confirmarLaReserva.Manejar(new ConfirmarLaReserva(evento.NumeroDelArriendo, alquilerYSeguroCobrados.ComprobanteDelAlquiler, alquilerYSeguroCobrados.ComprobanteDelSeguro, depositoBloqueado.AutorizacionDelBloqueoDelDeposito)));
    }

    /// <summary>"Cuenta del arriendo cerrada" de "Contexto Cobros y depósito" (id-d853efb4ccfe4d5c9b75522348b303df). Dispara "Registrar el avance del arriendo".</summary>
    public RespuestaDeEventoExterno Recibir(CuentaDelArriendoCerrada evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        return RespuestaDeEventoExterno.Ejecutado(registrarElAvanceDelArriendo.Manejar(new RegistrarElAvanceDelArriendo(evento.NumeroDelArriendo, AvanceDelArriendo.Cerrado, evento.FechaYHoraDelCambio)));
    }

    /// <summary>"Depósito bloqueado" de "Contexto Cobros y depósito" (id-41585106baae43ab90ca920de78dc737). Dispara "Confirmar la reserva" junto con Alquiler y seguro cobrados.</summary>
    public RespuestaDeEventoExterno Recibir(DepositoBloqueado evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        var juntos = espera.Anotar("Confirmar la reserva", ["Alquiler y seguro cobrados", "Depósito bloqueado"], evento, out var faltan);
        if (juntos is null)
        {
            return RespuestaDeEventoExterno.Esperando(faltan);
        }
        var alquilerYSeguroCobrados = (AlquilerYSeguroCobrados)juntos["Alquiler y seguro cobrados"];
        var depositoBloqueado = (DepositoBloqueado)juntos["Depósito bloqueado"];
        return RespuestaDeEventoExterno.Ejecutado(confirmarLaReserva.Manejar(new ConfirmarLaReserva(evento.NumeroDelArriendo, alquilerYSeguroCobrados.ComprobanteDelAlquiler, alquilerYSeguroCobrados.ComprobanteDelSeguro, depositoBloqueado.AutorizacionDelBloqueoDelDeposito)));
    }

    /// <summary>"Inspección de devolución registrada" de "Contexto Operación del arriendo" (id-d83f5b5cfb764e7aaac782ffab1b12c4). Dispara "Registrar el avance del arriendo".</summary>
    public RespuestaDeEventoExterno Recibir(InspeccionDeDevolucionRegistrada evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        return RespuestaDeEventoExterno.Ejecutado(registrarElAvanceDelArriendo.Manejar(new RegistrarElAvanceDelArriendo(evento.NumeroDelArriendo, AvanceDelArriendo.Devuelto, evento.FechaYHoraDelCambio)));
    }

    /// <summary>"Yate entregado al cliente" de "Contexto Operación del arriendo" (id-275970c646a74ac3ac7c206246d780ab). Dispara "Registrar el avance del arriendo".</summary>
    public RespuestaDeEventoExterno Recibir(YateEntregadoAlCliente evento)
    {
        bitacora.Anotar("evento recibido", evento.NombreEnElModelo, evento);
        return RespuestaDeEventoExterno.Ejecutado(registrarElAvanceDelArriendo.Manejar(new RegistrarElAvanceDelArriendo(evento.NumeroDelArriendo, AvanceDelArriendo.EnCurso, evento.FechaYHoraDelCambio)));
    }
}
