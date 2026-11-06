// Generado desde ArchiMate: ApplicationProcess "Registrar el acta de entrega" (SB-22, id-8addfcc26ad744b8a15ea09a54227d4d).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en RegistrarElActaDeEntrega.cs.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Entrada del comando "Registrar el acta de entrega" (SB-22).</summary>
public sealed record RegistrarElActaDeEntrega(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    List<string> Fotos,
    decimal NivelDeCombustible,
    DateTime HoraDeEntrega,
    string? Observaciones
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record RegistrarElActaDeEntregaDatos(
    RegistrarElActaDeEntrega Comando,
    ReservaConfirmada ReservaConfirmada
);

/// <summary>Manejador del comando "Registrar el acta de entrega" (SB-22).</summary>
/// <remarks>
/// <para>Contrato de servicio: Registrar el acta de entrega (id-cebe80de47aa4662af8631258f3353b5), asociado al servicio de negocio
/// "Registrar el acta de entrega" (id-736ac0345b2e45d1b2d5129325af2b9b), que el comando realiza.</para>
/// <para>Entrada: Arriendo, identificador del yate, fotos, nivel de combustible, hora de entrega y observaciones.</para>
/// <para>Salida: Acta de entrega registrada.</para>
/// <para>Reglas: Se rechaza si el arriendo no tiene la reserva confirmada (CIE-01) o si el acta no trae fotos (H-13). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class RegistrarElActaDeEntregaManejador(
    Repositorio<ActaDeEntrega> repositorio,
    BusDeEventos bus,
    MemoriaDeEventos memoria
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(RegistrarElActaDeEntregaDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(RegistrarElActaDeEntrega comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 1c. Eventos de otros contextos que el comando requiere (D5): si no han llegado para su identidad, 409.
        var reservaConfirmada = memoria.Buscar<ReservaConfirmada>("Reserva confirmada", comando.NumeroDelArriendo)
            ?? throw new FaltaEventoRequerido("Registrar el acta de entrega", "Reserva confirmada", comando.NumeroDelArriendo);

        // 4. Reglas del contrato (archivo manual).
        var datos = new RegistrarElActaDeEntregaDatos(comando, reservaConfirmada);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Su identidad se forma con datos;
        //    si ya existe una raíz con esa identidad, 409.
        var actaDeEntrega = new ActaDeEntrega
        {
            Estado = EstadoDelActaDeEntrega.Registrada,
            IdentificadorDelYate = comando.IdentificadorDelYate,
            Fotos = comando.Fotos,
            NivelDeCombustible = comando.NivelDeCombustible,
            HoraDeEntrega = comando.HoraDeEntrega,
            Observaciones = comando.Observaciones,
        };
        repositorio.Agregar(actaDeEntrega, $"{(comando.NumeroDelArriendo)}");

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new YateEntregadoAlCliente(actaDeEntrega.NumeroDelArriendo, comando.IdentificadorDelYate, comando.HoraDeEntrega), eventos);
        return new RespuestaDeComando(actaDeEntrega.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
