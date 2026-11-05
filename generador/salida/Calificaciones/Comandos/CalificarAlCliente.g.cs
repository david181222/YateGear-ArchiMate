// Generado desde ArchiMate: ApplicationProcess "Calificar al cliente" (SB-29, id-bc9ac3247ce043cfbaf82400004826b8).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en CalificarAlCliente.cs.
#nullable enable
namespace YateGear.Calificaciones;

/// <summary>Entrada del comando "Calificar al cliente" (SB-29).</summary>
public sealed record CalificarAlCliente(
    string NumeroDelArriendo,
    int CalificacionDada
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record CalificarAlClienteDatos(
    CalificarAlCliente Comando,
    ArriendoCerrado ArriendoCerrado
);

/// <summary>Manejador del comando "Calificar al cliente" (SB-29).</summary>
/// <remarks>
/// <para>Contrato de servicio: Calificar al cliente (id-f8d6e31e5be242919d71ef22e34a7824), asociado al servicio de negocio
/// "Calificar al cliente" (id-a527caed9bb24be8b7a18d595986b424), que el comando realiza.</para>
/// <para>Entrada: Arriendo cerrado y calificación.</para>
/// <para>Salida: Calificación registrada.</para>
/// <para>Reglas: Una calificación por cada parte y arriendo, al cerrar el arriendo (E2E-07); se rechaza si el arriendo no está cerrado o si el propietario ya calificó. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class CalificarAlClienteManejador(
    Repositorio<Calificacion> repositorio,
    BusDeEventos bus,
    MemoriaDeEventos memoria
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(CalificarAlClienteDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(CalificarAlCliente comando)
    {
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 1c. Eventos de otros contextos que el comando requiere (D5): si no han llegado para su identidad, 409.
        var arriendoCerrado = memoria.Buscar<ArriendoCerrado>("Arriendo cerrado", comando.NumeroDelArriendo)
            ?? throw new FaltaEventoRequerido("Calificar al cliente", "Arriendo cerrado", comando.NumeroDelArriendo);

        // 4. Reglas del contrato (archivo manual).
        var datos = new CalificarAlClienteDatos(comando, arriendoCerrado);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Su identidad se forma con datos;
        //    si ya existe una raíz con esa identidad, 409.
        var calificacion = new Calificacion
        {
            Estado = EstadoDeLaCalificacion.Registrada,
            QuienCalifica = ParteQueCalifica.Propietario,
            CalificacionDada = comando.CalificacionDada,
            Calificado = arriendoCerrado.ReferenciaAlCRM,
            NumeroDelArriendo = comando.NumeroDelArriendo,
        };
        repositorio.Agregar(calificacion, $"{(comando.NumeroDelArriendo)}/{(ParteQueCalifica.Propietario)}");

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new ClienteCalificado(calificacion.IdentificadorDeLaCalificacion, calificacion.Calificado, comando.CalificacionDada), eventos);
        return new RespuestaDeComando(calificacion.IdentificadorDeLaCalificacion, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
