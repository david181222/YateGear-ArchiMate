// Generado desde ArchiMate: ApplicationComponent "Contexto Cobros y depósito" (id-859686865fd4465397859188d62c971c).
// Registro del contexto en el programa (host): servicios, políticas y endpoints. No editar: el generador
// reescribe este archivo. El host llama a AgregarServicios y a MapearEndpoints.
#nullable enable
using System.Text.Json;
using YateGear.Integracion;

namespace YateGear.CobrosYDeposito;

/// <summary>Registra el contexto "Contexto Cobros y depósito" en el programa.</summary>
public static class Registro
{
    /// <summary>Nombre del contexto en la documentación de la API: agrupa sus endpoints.</summary>
    private const string Contexto = "Cobros y depósito";

    /// <summary>Servicios del contexto.</summary>
    public static void AgregarServicios(IServiceCollection servicios)
    {
        // Infraestructura (no sale del modelo): bitácora, bus de eventos y repositorio en memoria.
        // El bus del contexto publica también en el bus entre contextos, por nombre y en JSON (D1).
        servicios.AddSingleton<Bitacora>();
        servicios.AddSingleton(s => new BusDeEventos(s.GetRequiredService<Bitacora>(),
            s.GetRequiredService<BusEntreContextos>(), "Contexto Cobros y depósito"));
        servicios.AddSingleton(new Repositorio<CuentaDelArriendo>());
        servicios.AddSingleton(new Repositorio<DepositoParaDanos>());
        servicios.AddSingleton(new Repositorio<ReclamoALaAseguradora>("REC-", 4));

        // Servicios de la capa anticorrupción, simulados.
        servicios.AddSingleton<ICobrosPorLaPasarelaDePagos, CobrosPorLaPasarelaDePagosSimulado>();
        servicios.AddSingleton<IContratosConPropietariosYClientes, ContratosConPropietariosYClientesSimulado>();
        servicios.AddSingleton<IPolizasYReclamosDeLaAseguradora, PolizasYReclamosDeLaAseguradoraSimulado>();
        servicios.AddSingleton<IEmisorDeEnvioDeArriendosCerradosAFinanzas, EmisorDeEnvioDeArriendosCerradosAFinanzasSimulado>();          // solo envía (G11)

        // Manejadores de comandos y consultas.
        servicios.AddSingleton<BloquearElDepositoManejador>();
        servicios.AddSingleton<CerrarLasCuentasDelArriendoManejador>();
        servicios.AddSingleton<CobrarAlquilerYSeguroManejador>();
        servicios.AddSingleton<DescontarDanosDelDepositoManejador>();
        servicios.AddSingleton<LiberarElDepositoManejador>();
        servicios.AddSingleton<LiquidarYCobrarLosCargosDelCierreManejador>();
        servicios.AddSingleton<ReclamarElExcedenteDeDanosALaAseguradoraManejador>();
        servicios.AddSingleton<ReembolsarUnaCancelacionManejador>();
        servicios.AddSingleton<ConsultarElEstadoDeCuentaDelArriendoManejador>();

        // Lo que reciben los servicios SA (G7): un receptor por SA.
        servicios.AddSingleton<ReceptorDeContratosConPropietariosYClientes>();

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
        entreContextos.Suscribir("Contexto Operación del arriendo", "Diferencias determinadas",
            m => receptorEntreContextos.RecibirDiferenciasDeterminadas(m.DatosConIdentidad("numeroDelArriendo")));
        entreContextos.Suscribir("Contexto Gestión del arriendo", "Reserva cancelada",
            m => receptorEntreContextos.RecibirReservaCancelada(m.DatosConIdentidad("numeroDelArriendo")));

        // Comandos: POST con el comando en JSON.
        app.MapPost("/cobros-y-deposito/comandos/bloquear-el-deposito",
            (BloquearElDeposito comando, BloquearElDepositoManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-19: Bloquear el depósito",
                "Entrada: Arriendo, valor del depósito y tarjeta de crédito del cliente.\n\nSalida: Depósito bloqueado con su código de autorización y la fecha en que vence el bloqueo.\n\nReglas: Se rechaza si el bloqueo vencería antes del cierre: la autorización en tarjeta de crédito dura 28 días (V4-SUP-07, contraste de H-10). En la práctica, la fecha de fin del arriendo no puede pasar de unos 25 días después de reservar.", 404, 409, 422);
        app.MapPost("/cobros-y-deposito/comandos/cerrar-las-cuentas-del-arriendo",
            (CerrarLasCuentasDelArriendo comando, CerrarLasCuentasDelArriendoManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-17: Cerrar las cuentas del arriendo",
                "Entrada: Arriendo devuelto, sus cobros y la decisión sobre el depósito.\n\nSalida: Cuentas cerradas con el valor del alquiler, la comisión y el valor del propietario, enviados a Finanzas.\n\nReglas: Se rechaza mientras falte un cargo del cierre o la decisión sobre el depósito, porque con los ajustes se cierra el arriendo (E2E-01).", 404, 409, 422);
        app.MapPost("/cobros-y-deposito/comandos/cobrar-alquiler-y-seguro",
            (CobrarAlquilerYSeguro comando, CobrarAlquilerYSeguroManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-13: Cobrar alquiler y seguro",
                "Entrada: Arriendo, días, precio por día, valor del seguro y medio de pago del cliente.\n\nSalida: Comprobantes del alquiler y del seguro y número de la póliza.", 404, 409, 422);
        app.MapPost("/cobros-y-deposito/comandos/descontar-danos-del-deposito",
            (DescontarDanosDelDeposito comando, DescontarDanosDelDepositoManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-21: Descontar daños del depósito",
                "Entrada: Arriendo, valor de los daños y evidencia.\n\nSalida: Valor descontado, saldo liberado y valor que excede el depósito, si lo hay.\n\nReglas: Se rechaza un descuento sin evidencia (principio \"Todo cobro va con evidencia\", V1). Se hace en máximo 3 días después de la devolución (resultado de la V1). El valor de los daños llega con la inspección (V4-SUP-03).", 404, 409, 422);
        app.MapPost("/cobros-y-deposito/comandos/liberar-el-deposito",
            (LiberarElDeposito comando, LiberarElDepositoManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-20: Liberar el depósito",
                "Entrada: Arriendo e inspección sin daños, o arriendo cancelado con el depósito bloqueado.\n\nSalida: Depósito liberado y fecha de la liberación.\n\nReglas: Se rechaza si la inspección registró daños (REG-01). Se libera en máximo 3 días después de la devolución (resultado de la V1). Si la reserva se cancela, se libera al cancelar, sin inspección (V4-SUP-09).", 404, 409, 422);
        app.MapPost("/cobros-y-deposito/comandos/liquidar-y-cobrar-los-cargos-del-cierre",
            (LiquidarYCobrarLosCargosDelCierre comando, LiquidarYCobrarLosCargosDelCierreManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-14: Liquidar y cobrar los cargos del cierre",
                "Entrada: Arriendo, combustible consumido, horas adicionales y evidencia (actas y fotos de entrega e inspección).\n\nSalida: Cargos cobrados con su comprobante y la evidencia que los respalda.\n\nReglas: Se rechaza un cargo sin evidencia (principio \"Todo cobro va con evidencia\", V1). El combustible consumido siempre lo paga el cliente (REG-01).", 404, 409, 422);
        app.MapPost("/cobros-y-deposito/comandos/reclamar-el-excedente-de-danos-a-la-aseguradora",
            (ReclamarElExcedenteDeDanosALaAseguradora comando, ReclamarElExcedenteDeDanosALaAseguradoraManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-16: Reclamar el excedente de daños a la aseguradora",
                "Entrada: Arriendo, número de póliza, valor de los daños, valor descontado del depósito y evidencia.\n\nSalida: Reclamo enviado con su número y, cuando llegue, la respuesta de la aseguradora.\n\nReglas: Se rechaza si el daño no supera el depósito (REG-01) o si falta la evidencia de la entrega y de la inspección (EXC-02).", 404, 409, 422);
        app.MapPost("/cobros-y-deposito/comandos/reembolsar-una-cancelacion",
            (ReembolsarUnaCancelacion comando, ReembolsarUnaCancelacionManejador manejador) => Ejecutar(() => manejador.Manejar(comando)))
            .Documentar<RespuestaDeComando>("Comando SB-15: Reembolsar una cancelación",
                "Entrada: Arriendo cancelado, días de anticipación y condiciones de cancelación del contrato con el cliente.\n\nSalida: Valor devuelto con su comprobante, o la razón por la que no hay devolución.\n\nReglas: No se reembolsa la cancelación hecha muy cerca de la fecha; el plazo lo fija el contrato con el cliente (EXC-02, D-03).", 404, 409, 422);

        // Consultas: GET con la identidad en la ruta.
        app.MapGet("/cobros-y-deposito/consultas/consultar-el-estado-de-cuenta-del-arriendo/{numeroDelArriendo}",
            (string numeroDelArriendo, ConsultarElEstadoDeCuentaDelArriendoManejador manejador) => Ejecutar(() => manejador.Manejar(new ConsultarElEstadoDeCuentaDelArriendo(numeroDelArriendo))))
            .Documentar<ConsultarElEstadoDeCuentaDelArriendoSalida>("Consulta SB-18: Consultar el estado de cuenta del arriendo",
                "Entrada: Número de arriendo.\n\nSalida: Lista de movimientos con fecha, concepto, valor y evidencia.\n\nReglas: Se rechaza si quien consulta no es el cliente del arriendo ni un empleado de YateGear, porque son datos de pago (Ley 1581, H-19).", 404, 422);

        // Eventos de otros contextos (capa 3): POST con el evento en JSON. Si falta un dato obligatorio
        // responde 422; si faltan eventos de su grupo (junto_con), 202.
        app.MapPost("/cobros-y-deposito/eventos-externos/diferencias-determinadas",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirDiferenciasDeterminadas(evento), Recibido))
            .Accepts<DiferenciasDeterminadas>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Diferencias determinadas\" de Contexto Operación del arriendo",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);
        app.MapPost("/cobros-y-deposito/eventos-externos/reserva-cancelada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirReservaCancelada(evento), Recibido))
            .Accepts<ReservaCancelada>("application/json")
            .Documentar<RespuestaDeEventoExterno>("Evento \"Reserva cancelada\" de Contexto Gestión del arriendo",
                "Endpoint de prueba: entre contextos, el evento llega solo por el bus.", 202, 404, 409, 422);


        // Lo que reciben los servicios SA (G7): POST con el mensaje en JSON. Si falta un dato obligatorio responde 422.
        app.MapPost("/cobros-y-deposito/sa/contratos-con-propietarios-y-clientes/contrato-del-cliente-firmado",
            (JsonElement mensaje, ReceptorDeContratosConPropietariosYClientes receptor) => Ejecutar(() => receptor.RecibirContratoDelClienteFirmado(mensaje)))
            .Accepts<ContratoDelClienteFirmado>("application/json")
            .Documentar<RespuestaDeComando>("Mensaje \"Contrato del cliente firmado\" que recibe SA-02 Contratos con propietarios y clientes",
                "Lo que el sistema externo le envía a la aplicación. Dispara: Bloquear el depósito, Cobrar alquiler y seguro.", 404, 409, 422);

        // Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
        app.MapGet("/cobros-y-deposito/bitacora", (Bitacora bitacora) => bitacora.Todo())
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
