// Generado desde ArchiMate: ApplicationProcess "Enviar el aviso de reserva confirmada" (SB-31, id-57da84f53a9742cea51396bf297bf06d).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en EnviarElAvisoDeReservaConfirmada.cs.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada del comando "Enviar el aviso de reserva confirmada" (SB-31).</summary>
public sealed record EnviarElAvisoDeReservaConfirmada(
    string NumeroDelArriendo
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record EnviarElAvisoDeReservaConfirmadaDatos(
    EnviarElAvisoDeReservaConfirmada Comando,
    Arriendo Arriendo,
    AvisosYActasDeLasMarinasSalida AvisosYActasDeLasMarinas
);

/// <summary>Manejador del comando "Enviar el aviso de reserva confirmada" (SB-31).</summary>
/// <remarks>
/// <para>Contrato de servicio: Enviar el aviso de reserva confirmada (id-e3e5284cecbe41648a8d588b31e44156), asociado al servicio de negocio
/// "Enviar el aviso de reserva confirmada" (id-940b1b6a284743d4846e382782cd4a4e), que el comando realiza.</para>
/// <para>Entrada: Arriendo con la reserva confirmada.</para>
/// <para>Salida: Aviso enviado al propietario y a la marina con el yate, las fechas y el cliente.</para>
/// <para>Reglas: Se rechaza si la reserva no está confirmada: el aviso sale solo después de confirmar (H-07). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class EnviarElAvisoDeReservaConfirmadaManejador(
    Repositorio<Arriendo> repositorio,
    BusDeEventos bus,
    IAvisosYActasDeLasMarinas avisosYActasDeLasMarinas
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(EnviarElAvisoDeReservaConfirmadaDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(EnviarElAvisoDeReservaConfirmada comando)
    {
        // 1. Cargar la raíz.
        var arriendo = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe arriendo {comando.NumeroDelArriendo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Enviar el aviso de reserva confirmada", arriendo.Estado, EstadoDelArriendo.ReservaConfirmada);

        // 2. Servicios SA que usa, en orden.
        var respuestaAvisosYActasDeLasMarinas = avisosYActasDeLasMarinas.Llamar(new AvisosYActasDeLasMarinasEntrada(arriendo.YateDelArriendo.IdentificadorDelYate, arriendo.YateDelArriendo.Marina, arriendo.FechasDelArriendo.Inicio, arriendo.FechasDelArriendo.Fin, arriendo.FichaDelCliente.ReferenciaAlCRM));

        // 4. Reglas del contrato (archivo manual).
        var datos = new EnviarElAvisoDeReservaConfirmadaDatos(comando, arriendo, respuestaAvisosYActasDeLasMarinas);
        ValidarReglas(datos);

        // 6. El comando solo lee la raíz: no guarda.

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new AvisoDeReservaEnviado(arriendo.NumeroDelArriendo, respuestaAvisosYActasDeLasMarinas.ConstanciaDelAviso), eventos);
        return new RespuestaDeComando(arriendo.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
