// Generado desde ArchiMate: ApplicationComponent "Contexto Gestión del arriendo" (id-fdcc9b19f08a492f8ccd5dd4559926bc).
// Políticas del contexto: un evento dispara un comando del mismo contexto (relación de disparo del modelo).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Suscribe en el bus las políticas internas del contexto.</summary>
public static class Politicas
{
    /// <summary>Registra cada política.</summary>
    public static void Registrar(IServiceProvider servicios)
    {
        var bus = servicios.GetRequiredService<BusDeEventos>();

        // "Reserva confirmada" dispara "Enviar el aviso de reserva confirmada" (relación id-4bb3be2830b946619f18bcacda5e4eb4).
        bus.Suscribir<ReservaConfirmada>(e => servicios.GetRequiredService<EnviarElAvisoDeReservaConfirmadaManejador>()
            .Manejar(new EnviarElAvisoDeReservaConfirmada(e.NumeroDelArriendo)));

        // "Riesgo aceptable obtenido": "Contratos con propietarios y clientes" envía "Datos para el contrato del cliente" (lenguaje publicado, G11).
        bus.Suscribir<RiesgoAceptableObtenido>(e => servicios.GetRequiredService<IEmisorDeContratosConPropietariosYClientes>()
            .Enviar(new DatosParaElContratoDelCliente(e.NumeroDelArriendo, e.ReferenciaAlCRM, e.IdentificadorDelYate, e.Inicio, e.Fin, e.PrecioPorDia)));
    }
}
