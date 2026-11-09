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
            (CancelarLaReserva comando, CancelarLaReservaManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/gestion-del-arriendo/comandos/confirmar-la-reserva",
            (ConfirmarLaReserva comando, ConfirmarLaReservaManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/gestion-del-arriendo/comandos/enviar-el-aviso-de-reserva-confirmada",
            (EnviarElAvisoDeReservaConfirmada comando, EnviarElAvisoDeReservaConfirmadaManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/gestion-del-arriendo/comandos/obtener-el-nivel-de-riesgo-del-cliente",
            (ObtenerElNivelDeRiesgoDelCliente comando, ObtenerElNivelDeRiesgoDelClienteManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/gestion-del-arriendo/comandos/registrar-el-avance-del-arriendo",
            (RegistrarElAvanceDelArriendo comando, RegistrarElAvanceDelArriendoManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));
        app.MapPost("/gestion-del-arriendo/comandos/registrar-la-solicitud-de-reserva",
            (RegistrarLaSolicitudDeReserva comando, RegistrarLaSolicitudDeReservaManejador manejador) => Ejecutar(() => manejador.Manejar(comando)));

        // Consultas: GET con la identidad en la ruta.
        app.MapGet("/gestion-del-arriendo/consultas/consultar-el-arriendo/{numeroDelArriendo}",
            (string numeroDelArriendo, ConsultarElArriendoManejador manejador) => Ejecutar(() => manejador.Manejar(new ConsultarElArriendo(numeroDelArriendo))));
        app.MapGet("/gestion-del-arriendo/consultas/verificar-los-requisitos-del-cliente/{numeroDelArriendo}",
            (string numeroDelArriendo, VerificarLosRequisitosDelClienteManejador manejador) => Ejecutar(() => manejador.Manejar(new VerificarLosRequisitosDelCliente(numeroDelArriendo))));

        // Eventos de otros contextos (capa 3): POST con el evento en JSON. Si falta un dato obligatorio
        // responde 422; si faltan eventos de su grupo (junto_con), 202.
        app.MapPost("/gestion-del-arriendo/eventos-externos/alquiler-y-seguro-cobrados",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirAlquilerYSeguroCobrados(evento), Recibido));
        app.MapPost("/gestion-del-arriendo/eventos-externos/cuenta-del-arriendo-cerrada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirCuentaDelArriendoCerrada(evento), Recibido));
        app.MapPost("/gestion-del-arriendo/eventos-externos/deposito-bloqueado",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirDepositoBloqueado(evento), Recibido));
        app.MapPost("/gestion-del-arriendo/eventos-externos/inspeccion-de-devolucion-registrada",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirInspeccionDeDevolucionRegistrada(evento), Recibido));
        app.MapPost("/gestion-del-arriendo/eventos-externos/yate-entregado-al-cliente",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirYateEntregadoAlCliente(evento), Recibido));
        app.MapPost("/gestion-del-arriendo/eventos-externos/yate-registrado",
            (JsonElement evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.RecibirYateRegistrado(evento), Recibido));


        // Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
        app.MapGet("/gestion-del-arriendo/bitacora", (Bitacora bitacora) => bitacora.Todo());
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
