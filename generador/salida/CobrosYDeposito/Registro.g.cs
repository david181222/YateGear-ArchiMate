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
            (BloquearElDeposito comando, BloquearElDepositoManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/cobros-y-deposito/comandos/cerrar-las-cuentas-del-arriendo",
            (CerrarLasCuentasDelArriendo comando, CerrarLasCuentasDelArriendoManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/cobros-y-deposito/comandos/cobrar-alquiler-y-seguro",
            (CobrarAlquilerYSeguro comando, CobrarAlquilerYSeguroManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/cobros-y-deposito/comandos/descontar-danos-del-deposito",
            (DescontarDanosDelDeposito comando, DescontarDanosDelDepositoManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/cobros-y-deposito/comandos/liberar-el-deposito",
            (LiberarElDeposito comando, LiberarElDepositoManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/cobros-y-deposito/comandos/liquidar-y-cobrar-los-cargos-del-cierre",
            (LiquidarYCobrarLosCargosDelCierre comando, LiquidarYCobrarLosCargosDelCierreManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/cobros-y-deposito/comandos/reclamar-el-excedente-de-danos-a-la-aseguradora",
            (ReclamarElExcedenteDeDanosALaAseguradora comando, ReclamarElExcedenteDeDanosALaAseguradoraManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/cobros-y-deposito/comandos/reembolsar-una-cancelacion",
            (ReembolsarUnaCancelacion comando, ReembolsarUnaCancelacionManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));

        // Consultas: GET con la identidad en la ruta.
        app.MapGet("/cobros-y-deposito/consultas/consultar-el-estado-de-cuenta-del-arriendo/{numeroDelArriendo}",
            (string numeroDelArriendo, ConsultarElEstadoDeCuentaDelArriendoManejador manejador) => Ejecutar(() => manejador.Manejar(new ConsultarElEstadoDeCuentaDelArriendo(numeroDelArriendo))));

        // Eventos de otros contextos (capa 3): POST con el evento en JSON. Si falta un dato obligatorio
        // responde 422; si faltan eventos de su grupo (junto_con), 202.
        app.MapPost("/cobros-y-deposito/eventos-externos/diferencias-determinadas",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirDiferenciasDeterminadas(evento), Recibido));
        app.MapPost("/cobros-y-deposito/eventos-externos/reserva-cancelada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirReservaCancelada(evento), Recibido));


        // Lo que reciben los servicios SA (G7): POST con el mensaje en JSON. Si falta un dato obligatorio responde 422.
        app.MapPost("/cobros-y-deposito/sa/contratos-con-propietarios-y-clientes/contrato-del-cliente-firmado",
            (JsonElement mensaje, ReceptorDeContratosConPropietariosYClientes receptor) => Ejecutar(() => receptor.RecibirContratoDelClienteFirmado(mensaje)));

        // Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
        app.MapGet("/cobros-y-deposito/bitacora", (Bitacora bitacora) => bitacora.Todo());
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
