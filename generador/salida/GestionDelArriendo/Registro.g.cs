// Generado desde ArchiMate: ApplicationComponent "Contexto Gestión del arriendo" (id-fdcc9b19f08a492f8ccd5dd4559926bc).
// Registro del contexto en el programa (host): servicios, políticas y endpoints. No editar: el generador
// reescribe este archivo. El host llama a AgregarServicios y a MapearEndpoints.
#nullable enable
using System.Text.Json;
using YateGear.Integracion;

namespace YateGear.GestionDelArriendo;

/// <summary>Registra el contexto "Contexto Gestión del arriendo" en el programa.</summary>
public static class Registro
{
    /// <summary>Nombre del contexto en la documentación de la API: agrupa sus endpoints.</summary>
    private const string Contexto = "Gestión del arriendo";

    /// <summary>Servicios del contexto.</summary>
    public static void AgregarServicios(IServiceCollection servicios)
    {
        // Infraestructura (no sale del modelo): bitácora, bus de eventos y repositorio en memoria.
        // El bus del contexto publica también en el bus entre contextos, por nombre y en JSON (D1).
        servicios.AddSingleton<Bitacora>();
        servicios.AddSingleton(s => new BusDeEventos(s.GetRequiredService<Bitacora>(),
            s.GetRequiredService<BusEntreContextos>(), "Contexto Gestión del arriendo"));
        servicios.AddSingleton(new Repositorio<Arriendo>("ARR-", 4));
        servicios.AddSingleton<MemoriaDeEventos>();

        // Servicios de la capa anticorrupción, simulados.
        servicios.AddSingleton<IAvisosYActasDeLasMarinas, AvisosYActasDeLasMarinasSimulado>();
        servicios.AddSingleton<IClientesDelCRM, ClientesDelCRMSimulado>();
        servicios.AddSingleton<IContratosConPropietariosYClientes, ContratosConPropietariosYClientesSimulado>();
        servicios.AddSingleton<INivelDeRiesgoDeLaEvaluadora, NivelDeRiesgoDeLaEvaluadoraSimulado>();
        servicios.AddSingleton<IEmisorDeContratosConPropietariosYClientes, EmisorDeContratosConPropietariosYClientesSimulado>();          // solo envía (G11)

        // Manejadores de comandos y consultas.
        servicios.AddSingleton<CancelarLaReservaManejador>();
        servicios.AddSingleton<ConfirmarLaReservaManejador>();
        servicios.AddSingleton<EnviarElAvisoDeReservaConfirmadaManejador>();
        servicios.AddSingleton<ObtenerElNivelDeRiesgoDelClienteManejador>();
        servicios.AddSingleton<RegistrarElAvanceDelArriendoManejador>();
        servicios.AddSingleton<RegistrarLaSolicitudDeReservaManejador>();
        servicios.AddSingleton<ConsultarElArriendoManejador>();
        servicios.AddSingleton<VerificarLosRequisitosDelClienteManejador>();

        // Eventos de otros contextos (capa 3): receptor y espera de los que deben llegar juntos.
        servicios.AddSingleton<EsperaDeEventos>();
        servicios.AddSingleton<ReceptorDeEventosExternos>();
    }

    /// <summary>Políticas y endpoints del contexto.</summary>
    public static void MapearEndpoints(WebApplication app)
    {
        Politicas.Registrar(app.Services);

        // Eventos de otros contextos que llegan por el bus entre contextos (G12, D1): cada uno va a su receptor, por el
        // nombre del contexto que lo publica y su nombre en el modelo. Si el receptor falla, el error queda en el bus.
        var entreContextos = app.Services.GetRequiredService<BusEntreContextos>();
        var receptorEntreContextos = app.Services.GetRequiredService<ReceptorDeEventosExternos>();
        entreContextos.Suscribir("Contexto Cobros y depósito", "Alquiler y seguro cobrados",
            m => receptorEntreContextos.RecibirAlquilerYSeguroCobrados(m.DatosConIdentidad("numeroDelArriendo")));
        entreContextos.Suscribir("Contexto Cobros y depósito", "Cuenta del arriendo cerrada",
            m => receptorEntreContextos.RecibirCuentaDelArriendoCerrada(m.DatosConIdentidad("numeroDelArriendo")));
        entreContextos.Suscribir("Contexto Cobros y depósito", "Depósito bloqueado",
            m => receptorEntreContextos.RecibirDepositoBloqueado(m.DatosConIdentidad("numeroDelArriendo")));
        entreContextos.Suscribir("Contexto Operación del arriendo", "Inspección de devolución registrada",
            m => receptorEntreContextos.RecibirInspeccionDeDevolucionRegistrada(m.DatosConIdentidad("numeroDelArriendo")));
        entreContextos.Suscribir("Contexto Operación del arriendo", "Yate entregado al cliente",
            m => receptorEntreContextos.RecibirYateEntregadoAlCliente(m.DatosConIdentidad("numeroDelArriendo")));
        entreContextos.Suscribir("Contexto Disponibilidad de yates", "Yate registrado",
            m => receptorEntreContextos.RecibirYateRegistrado(m.DatosConIdentidad("identificadorDelYate")));

        // Comandos: POST con el comando en JSON.
        app.MapPost("/gestion-del-arriendo/comandos/cancelar-la-reserva",
            (CancelarLaReserva comando, CancelarLaReservaManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-08: Cancelar la reserva",
                "Entrada: Arriendo, quién cancela y fecha de la cancelación.\n\nSalida: Arriendo cancelado y días de anticipación frente a la fecha de inicio.\n\nReglas: Se rechaza si el arriendo ya empezó: la cancelación es antes de la fecha del arriendo (EXC-02). La anticipación que da derecho a reembolso está en el contrato con el cliente (D-03).", 404, 409, 422);
        app.MapPost("/gestion-del-arriendo/comandos/confirmar-la-reserva",
            (ConfirmarLaReserva comando, ConfirmarLaReservaManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-07: Confirmar la reserva",
                "Entrada: Arriendo, evaluación de riesgo aceptable, referencia del contrato firmado, comprobantes del alquiler y del seguro y autorización del bloqueo del depósito.\n\nSalida: Arriendo en estado reserva confirmada.\n\nReglas: No se confirma sin riesgo aceptable, contrato firmado y pagos completos (REG-01); si falta uno, se rechaza indicando cuál.", 404, 409, 422);
        app.MapPost("/gestion-del-arriendo/comandos/enviar-el-aviso-de-reserva-confirmada",
            (EnviarElAvisoDeReservaConfirmada comando, EnviarElAvisoDeReservaConfirmadaManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-31: Enviar el aviso de reserva confirmada",
                "Entrada: Arriendo con la reserva confirmada.\n\nSalida: Aviso enviado al propietario y a la marina con el yate, las fechas y el cliente.\n\nReglas: Se rechaza si la reserva no está confirmada: el aviso sale solo después de confirmar (H-07).", 404, 409, 422);
        app.MapPost("/gestion-del-arriendo/comandos/obtener-el-nivel-de-riesgo-del-cliente",
            (ObtenerElNivelDeRiesgoDelCliente comando, ObtenerElNivelDeRiesgoDelClienteManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-12: Obtener el nivel de riesgo del cliente",
                "Entrada: Arriendo y datos del cliente que autorizó compartir.\n\nSalida: Nivel de riesgo (bajo, medio o alto) y decisión: aceptable o no se arrienda.\n\nReglas: Con riesgo alto el arriendo no se realiza (REG-01); aceptable es bajo o medio (V4-SUP-02). No se envían datos a la evaluadora sin la autorización del cliente (H-19).", 404, 409, 422);
        app.MapPost("/gestion-del-arriendo/comandos/registrar-el-avance-del-arriendo",
            (RegistrarElAvanceDelArriendo comando, RegistrarElAvanceDelArriendoManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-09: Registrar el avance del arriendo",
                "Entrada: Arriendo, nuevo estado y fecha y hora del cambio.\n\nSalida: Arriendo con el estado actualizado.\n\nReglas: Se rechaza cerrar el arriendo antes de terminar los ajustes de dinero, porque con ellos se cierra (E2E-01).", 404, 409, 422);
        app.MapPost("/gestion-del-arriendo/comandos/registrar-la-solicitud-de-reserva",
            (RegistrarLaSolicitudDeReserva comando, RegistrarLaSolicitudDeReservaManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-06: Registrar la solicitud de reserva",
                "Entrada: Cliente, yate, fecha de inicio, fecha de fin, licencia de navegación (número y vigencia) y autorización para el tratamiento de datos.\n\nSalida: Arriendo con su número, en estado reserva solicitada, y ficha del cliente actualizada.", 404, 409, 422);

        // Consultas: GET con la identidad en la ruta.
        app.MapGet("/gestion-del-arriendo/consultas/consultar-el-arriendo/{numeroDelArriendo}",
            (string numeroDelArriendo, ConsultarElArriendoManejador manejador) => Ejecutar(() => manejador.Manejar(new ConsultarElArriendo(numeroDelArriendo))))
            .Documentar<ConsultarElArriendoSalida>("Consulta SB-10: Consultar el arriendo",
                "Entrada: Número de arriendo.\n\nSalida: Cliente, yate, marina, fechas y estado del arriendo.\n\nReglas: Se rechaza si quien consulta no participa en el arriendo, porque son datos personales del cliente (Ley 1581, H-19).", 404, 422);
        app.MapGet("/gestion-del-arriendo/consultas/verificar-los-requisitos-del-cliente/{numeroDelArriendo}",
            (string numeroDelArriendo, VerificarLosRequisitosDelClienteManejador manejador) => Ejecutar(() => manejador.Manejar(new VerificarLosRequisitosDelCliente(numeroDelArriendo))))
            .Documentar<VerificarLosRequisitosDelClienteSalida>("Consulta SB-11: Verificar los requisitos del cliente",
                "Entrada: Cliente, número y vigencia de la licencia de navegación y autorización de datos (fecha y terceros autorizados: evaluadora, aseguradora y pasarela).\n\nSalida: Cumple o no cumple, con el motivo.\n\nReglas: Se rechaza sin licencia de navegación vigente (H-09, NOR-01) o sin autorización del cliente para compartir sus datos con terceros (Ley 1581, H-19).", 404, 422);

        // Eventos de otros contextos (capa 3): POST con el evento en JSON. Si falta un dato obligatorio
        // responde 422; si faltan eventos de su grupo (junto_con), 202.
        app.MapPost("/gestion-del-arriendo/eventos-externos/alquiler-y-seguro-cobrados",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirAlquilerYSeguroCobrados(evento), Recibido))
            .Accepts<AlquilerYSeguroCobrados>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Alquiler y seguro cobrados\" de Contexto Cobros y depósito",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);
        app.MapPost("/gestion-del-arriendo/eventos-externos/cuenta-del-arriendo-cerrada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirCuentaDelArriendoCerrada(evento), Recibido))
            .Accepts<CuentaDelArriendoCerrada>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Cuenta del arriendo cerrada\" de Contexto Cobros y depósito",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);
        app.MapPost("/gestion-del-arriendo/eventos-externos/deposito-bloqueado",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirDepositoBloqueado(evento), Recibido))
            .Accepts<DepositoBloqueado>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Depósito bloqueado\" de Contexto Cobros y depósito",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);
        app.MapPost("/gestion-del-arriendo/eventos-externos/inspeccion-de-devolucion-registrada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirInspeccionDeDevolucionRegistrada(evento), Recibido))
            .Accepts<InspeccionDeDevolucionRegistrada>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Inspección de devolución registrada\" de Contexto Operación del arriendo",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);
        app.MapPost("/gestion-del-arriendo/eventos-externos/yate-entregado-al-cliente",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirYateEntregadoAlCliente(evento), Recibido))
            .Accepts<YateEntregadoAlCliente>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Yate entregado al cliente\" de Contexto Operación del arriendo",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);
        app.MapPost("/gestion-del-arriendo/eventos-externos/yate-registrado",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirYateRegistrado(evento), Recibido))
            .Accepts<YateRegistrado>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Yate registrado\" de Contexto Disponibilidad de yates",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);


        // Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
        app.MapGet("/gestion-del-arriendo/bitacora", (Bitacora bitacora) => bitacora.Todo())
            .Documentar<IReadOnlyList<RegistroDeBitacora>>("Bitácora (infraestructura)",
                "Eventos publicados y recibidos, llamadas a los servicios SA simulados y errores, en orden. No sale del modelo.");
    }

    /// <summary>Documenta un endpoint para OpenAPI (Swagger): su contexto, de qué elemento del modelo sale, su contrato,
    /// lo que responde y los códigos con que puede rechazar.</summary>
    private static RouteHandlerBuilder Documentar<TRespuesta>(this RouteHandlerBuilder endpoint, string resumen,
        string descripcion, params int[] rechazos)
    {
        endpoint.WithTags(Contexto).WithSummary(resumen).WithDescription(descripcion).Produces<TRespuesta>();
        foreach (var codigo in rechazos)
        {
            endpoint.Produces(codigo);
        }
        return endpoint;
    }

    private static IResult Ejecutar<T>(Func<T> accion, Func<T, IResult>? exito = null)
    {
        try
        {
            var resultado = accion();
            return exito is null ? Results.Ok(resultado) : exito(resultado);
        }
        catch (NoEncontrado e)
        {
            return Results.NotFound(new { error = e.Message });
        }
        catch (TransicionInvalida e)
        {
            return Results.Conflict(new { operacion = e.Operacion, estadoActual = e.EstadoActual, permitidos = e.Permitidos });
        }
        catch (ReglaIncumplida e)
        {
            return Results.UnprocessableEntity(new { regla = e.Regla, motivo = e.Motivo });
        }
        catch (IdentidadRepetida e)
        {
            return Results.Conflict(new { identidad = e.Identidad, motivo = e.Message });
        }
        catch (FaltaEventoRequerido e)
        {
            return Results.Conflict(new { operacion = e.Operacion, requiere = e.Evento, identidad = e.Identidad });
        }
        catch (DatoFaltante e)
        {
            return Results.UnprocessableEntity(new { regla = "dato faltante", motivo = e.Message });
        }
        catch (JsonException e)
        {
            return Results.BadRequest(new { error = e.Message });
        }
    }

    private static IResult Recibido(RespuestaDeEventoExterno respuesta) =>
        respuesta.Estado == "esperando" ? Results.Accepted(null, respuesta) : Results.Ok(respuesta);
}
