// Generado desde ArchiMate: ApplicationProcess "Calificar al propietario" (SB-28, id-b058bd36e7784e5ea81ab24c8dd3a4bb).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en CalificarAlPropietario.cs.
#nullable enable
namespace YateGear.Calificaciones;

/// <summary>Entrada del comando "Calificar al propietario" (SB-28).</summary>
public sealed record CalificarAlPropietario(
    string NumeroDelArriendo,
    int CalificacionDada
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record CalificarAlPropietarioDatos(
    CalificarAlPropietario Comando,
    ArriendoCerrado ArriendoCerrado
);

/// <summary>Manejador del comando "Calificar al propietario" (SB-28).</summary>
/// <remarks>
/// <para>Contrato de servicio: Calificar al propietario (id-c5fdbb67cdcb45b8a47cdc8a46a4f270), asociado al servicio de negocio
/// "Calificar al propietario" (id-ffefcf9db5cc44e2b460af1e53495558), que el comando realiza.</para>
/// <para>Entrada: Arriendo cerrado y calificación.</para>
/// <para>Salida: Calificación registrada.</para>
/// <para>Reglas: Una calificación por cada parte y arriendo, al cerrar el arriendo (E2E-07); se rechaza si el arriendo no está cerrado o si el cliente ya calificó. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class CalificarAlPropietarioManejador(
    Repositorio<Calificacion> repositorio,
    BusDeEventos bus,
    MemoriaDeEventos memoria
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(CalificarAlPropietarioDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(CalificarAlPropietario comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 1c. Eventos de otros contextos que el comando requiere (D5): si no han llegado para su identidad, 409.
        var arriendoCerrado = memoria.Buscar<ArriendoCerrado>("Arriendo cerrado", comando.NumeroDelArriendo)
            ?? throw new FaltaEventoRequerido("Calificar al propietario", "Arriendo cerrado", comando.NumeroDelArriendo);

        // 4. Reglas del contrato (archivo manual).
        var datos = new CalificarAlPropietarioDatos(comando, arriendoCerrado);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Su identidad se forma con datos;
        //    si ya existe una raíz con esa identidad, 409.
        var calificacion = new Calificacion
        {
            Estado = EstadoDeLaCalificacion.Registrada,
            QuienCalifica = ParteQueCalifica.Cliente,
            CalificacionDada = comando.CalificacionDada,
            Calificado = arriendoCerrado.Propietario,
            NumeroDelArriendo = comando.NumeroDelArriendo,
        };
        repositorio.Agregar(calificacion, $"{(comando.NumeroDelArriendo)}/{(ParteQueCalifica.Cliente)}");

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new PropietarioCalificado(calificacion.IdentificadorDeLaCalificacion, calificacion.Calificado, comando.CalificacionDada), eventos);
        return new RespuestaDeComando(calificacion.IdentificadorDeLaCalificacion, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
