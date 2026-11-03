// Generado desde ArchiMate: ApplicationComponent "Contexto Gestión del arriendo" (id-fdcc9b19f08a492f8ccd5dd4559926bc).
// Programa del contexto: servicios, políticas y endpoints. No editar: el generador reescribe este archivo.
// El puerto (5080) sale de PUERTO en src/generar.py; para una sola vez: ejecutar.ps1 -Puerto.
#nullable enable
using System.Text.Json.Serialization;
using YateGear.GestionDelArriendo;

var builder = WebApplication.CreateBuilder(args);
builder.Services.ConfigureHttpJsonOptions(o => o.SerializerOptions.Converters.Add(new JsonStringEnumConverter()));

// Infraestructura (no sale del modelo): bitácora, bus de eventos y repositorio en memoria.
builder.Services.AddSingleton<Bitacora>();
builder.Services.AddSingleton<BusDeEventos>();
builder.Services.AddSingleton(new Repositorio<Arriendo>("ARR-", 4));

// Servicios de la capa anticorrupción, simulados.
builder.Services.AddSingleton<IAvisosYActasDeLasMarinas, AvisosYActasDeLasMarinasSimulado>();
builder.Services.AddSingleton<IClientesDelCRM, ClientesDelCRMSimulado>();
builder.Services.AddSingleton<IContratosConPropietariosYClientes, ContratosConPropietariosYClientesSimulado>();
builder.Services.AddSingleton<INivelDeRiesgoDeLaEvaluadora, NivelDeRiesgoDeLaEvaluadoraSimulado>();

// Manejadores de comandos y consultas.
builder.Services.AddSingleton<CancelarLaReservaManejador>();
builder.Services.AddSingleton<ConfirmarLaReservaManejador>();
builder.Services.AddSingleton<EnviarElAvisoDeReservaConfirmadaManejador>();
builder.Services.AddSingleton<ObtenerElNivelDeRiesgoDelClienteManejador>();
builder.Services.AddSingleton<RegistrarElAvanceDelArriendoManejador>();
builder.Services.AddSingleton<RegistrarLaSolicitudDeReservaManejador>();
builder.Services.AddSingleton<ConsultarElArriendoManejador>();
builder.Services.AddSingleton<VerificarLosRequisitosDelClienteManejador>();

// Eventos de otros contextos (capa 3): receptor y espera de los que deben llegar juntos.
builder.Services.AddSingleton<EsperaDeEventos>();
builder.Services.AddSingleton<ReceptorDeEventosExternos>();

var app = builder.Build();
Politicas.Registrar(app.Services);

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


// Eventos de otros contextos (capa 3): POST con el evento en JSON. Responde 202 si faltan eventos de su grupo.
app.MapPost("/gestion-del-arriendo/eventos-externos/alquiler-y-seguro-cobrados",
    (AlquilerYSeguroCobrados evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.Recibir(evento), Recibido));
app.MapPost("/gestion-del-arriendo/eventos-externos/cuenta-del-arriendo-cerrada",
    (CuentaDelArriendoCerrada evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.Recibir(evento), Recibido));
app.MapPost("/gestion-del-arriendo/eventos-externos/deposito-bloqueado",
    (DepositoBloqueado evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.Recibir(evento), Recibido));
app.MapPost("/gestion-del-arriendo/eventos-externos/inspeccion-de-devolucion-registrada",
    (InspeccionDeDevolucionRegistrada evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.Recibir(evento), Recibido));
app.MapPost("/gestion-del-arriendo/eventos-externos/yate-entregado-al-cliente",
    (YateEntregadoAlCliente evento, ReceptorDeEventosExternos receptor) => Ejecutar(() => receptor.Recibir(evento), Recibido));

// Bitácora (infraestructura, no sale del modelo): eventos y llamadas a los servicios SA simulados, en orden.
app.MapGet("/gestion-del-arriendo/bitacora", (Bitacora bitacora) => bitacora.Todo());

app.Run();

static IResult Ejecutar<T>(Func<T> accion, Func<T, IResult>? exito = null)
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
    catch (DatoFaltante e)
    {
        return Results.UnprocessableEntity(new { regla = "dato faltante", motivo = e.Message });
    }
}

static IResult Recibido(RespuestaDeEventoExterno respuesta) =>
    respuesta.Estado == "esperando" ? Results.Accepted(null, respuesta) : Results.Ok(respuesta);
