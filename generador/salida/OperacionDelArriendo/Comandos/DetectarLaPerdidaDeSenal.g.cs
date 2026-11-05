// Generado desde ArchiMate: ApplicationProcess "Detectar la pérdida de señal" (SB-27, id-c742e57f7d34406c8162646ca3080c19).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en DetectarLaPerdidaDeSenal.cs.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Entrada del comando "Detectar la pérdida de señal" (SB-27).</summary>
public sealed record DetectarLaPerdidaDeSenal(
    int MinutosSinLecturas,
    DateTime Ahora
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record DetectarLaPerdidaDeSenalDatos(
    DetectarLaPerdidaDeSenal Comando,
    IReadOnlyList<LecturaDeUbicacionYCombustible> Raices,
    IReadOnlyList<ActaDeInspeccion> ActaDeInspeccion,
    IReadOnlyList<ActaDeEntrega> ActaDeEntrega
);

/// <summary>Manejador del comando "Detectar la pérdida de señal" (SB-27).</summary>
/// <remarks>
/// <para>Contrato de servicio: Detectar la pérdida de señal (id-28e93eb31c154c3dacd73eaf420c10ce), asociado al servicio de negocio
/// "Detectar la pérdida de señal" (id-3d8ae4cce1f145d0b041c733fe4bb970), que el comando realiza.</para>
/// <para>Entrada: Arriendo en curso y tiempo máximo sin lecturas.</para>
/// <para>Salida: Alerta de pérdida de señal con la última lectura conocida.</para>
/// <para>Reglas: El tiempo sin lecturas que dispara la alerta lo fija Operaciones (V4-SUP-04). Contactar al cliente lo hace la marina; el software solo detecta y avisa (EXC-01). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class DetectarLaPerdidaDeSenalManejador(
    Repositorio<LecturaDeUbicacionYCombustible> repositorio,
    BusDeEventos bus,
    Repositorio<ActaDeInspeccion> repositorioActaDeInspeccion,
    Repositorio<ActaDeEntrega> repositorioActaDeEntrega
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(DetectarLaPerdidaDeSenalDatos datos);

    /// <summary>Elige las raíces por las que se publica un evento (comando sobre todas, G8). Se escribe en el archivo manual.</summary>
    private partial IEnumerable<LecturaDeUbicacionYCombustible> Seleccionar(DetectarLaPerdidaDeSenalDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(DetectarLaPerdidaDeSenal comando)
    {
        // Sobre todas las raíces (G8): el archivo manual elige cuáles; se publica un evento por cada una.
        var raices = repositorio.Todas();
        var datos = new DetectarLaPerdidaDeSenalDatos(comando, raices, repositorioActaDeInspeccion.Todas(), repositorioActaDeEntrega.Todas());
        ValidarReglas(datos);
        var eventos = new List<string>();
        var elegidas = Seleccionar(datos).ToList();
        foreach (var lecturaDeUbicacionYCombustible in elegidas)
        {
            Publicar(new PerdidaDeSenalDelYate(lecturaDeUbicacionYCombustible.IdentificadorDeLaLectura, lecturaDeUbicacionYCombustible.IdentificadorDelYate, lecturaDeUbicacionYCombustible.Latitud, lecturaDeUbicacionYCombustible.Longitud, lecturaDeUbicacionYCombustible.NivelDeCombustible, lecturaDeUbicacionYCombustible.HoraDeLaLectura), eventos);
        }
        return new RespuestaDeComando(elegidas.Count == 1 ? elegidas[0].IdentificadorDeLaLectura : "", eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}

/// <summary>Corre "Detectar la pérdida de señal" cada 5 minutos (temporizador del YAML, G8). Si falla,
/// el error queda en la bitácora y la próxima revisión corre igual.</summary>
public sealed class DetectarLaPerdidaDeSenalTemporizador(DetectarLaPerdidaDeSenalManejador manejador, Bitacora bitacora) : BackgroundService
{
    /// <summary>Revisa cada 5 minutos hasta que la aplicación se detiene.</summary>
    protected override async Task ExecuteAsync(CancellationToken detener)
    {
        using var reloj = new PeriodicTimer(TimeSpan.FromMinutes(5));
        while (await reloj.WaitForNextTickAsync(detener))
        {
            try
            {
                manejador.Manejar(new DetectarLaPerdidaDeSenal(30, DateTime.Now));
            }
            catch (Exception e)
            {
                bitacora.Anotar("error del temporizador", "Detectar la pérdida de señal", e.Message);
            }
        }
    }
}
