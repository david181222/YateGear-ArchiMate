// Generado desde ArchiMate: ApplicationProcess "Determinar las diferencias entre entrega y devolución" (SB-24, id-8222df5442934cf5a117ced88ec7329e).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en DeterminarLasDiferenciasEntreEntregaYDevolucion.cs.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Entrada del comando "Determinar las diferencias entre entrega y devolución" (SB-24).</summary>
public sealed record DeterminarLasDiferenciasEntreEntregaYDevolucion(
    string NumeroDelArriendo
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record DeterminarLasDiferenciasEntreEntregaYDevolucionDatos(
    DeterminarLasDiferenciasEntreEntregaYDevolucion Comando,
    ActaDeInspeccion ActaDeInspeccion,
    ReservaConfirmada ReservaConfirmada,
    ActaDeEntrega ActaDeEntrega
);

/// <summary>Manejador del comando "Determinar las diferencias entre entrega y devolución" (SB-24).</summary>
/// <remarks>
/// <para>Contrato de servicio: Determinar las diferencias entre entrega y devolución (id-970ca0e1b9194b2d8fc058310bb1fca9), asociado al servicio de negocio
/// "Determinar las diferencias entre entrega y devolución" (id-c449f2eaf8144f35a8199dba2f395c65), que el comando realiza.</para>
/// <para>Entrada: Arriendo y fecha y hora de fin acordadas.</para>
/// <para>Salida: Combustible consumido, horas adicionales y daños, con la evidencia de cada uno.</para>
/// <para>Reglas: Se rechaza si falta el acta de entrega o la de inspección, porque la comparación de las dos es la evidencia (H-13). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class DeterminarLasDiferenciasEntreEntregaYDevolucionManejador(
    Repositorio<ActaDeInspeccion> repositorio,
    BusDeEventos bus,
    MemoriaDeEventos memoria,
    Repositorio<ActaDeEntrega> repositorioActaDeEntrega
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(DeterminarLasDiferenciasEntreEntregaYDevolucionDatos datos);

    /// <summary>Dato calculado "combustible consumido" del evento "Diferencias determinadas". Se escribe en el archivo manual.</summary>
    private partial decimal CombustibleConsumido(DeterminarLasDiferenciasEntreEntregaYDevolucionDatos datos);

    /// <summary>Dato calculado "horas adicionales" del evento "Diferencias determinadas". Se escribe en el archivo manual.</summary>
    private partial decimal HorasAdicionales(DeterminarLasDiferenciasEntreEntregaYDevolucionDatos datos);

    /// <summary>Dato calculado "valor de los daños" del evento "Diferencias determinadas". Se escribe en el archivo manual.</summary>
    private partial decimal ValorDeLosDanos(DeterminarLasDiferenciasEntreEntregaYDevolucionDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(DeterminarLasDiferenciasEntreEntregaYDevolucion comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. Cargar la raíz.
        var actaDeInspeccion = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe acta de inspección {comando.NumeroDelArriendo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Determinar las diferencias entre entrega y devolución", actaDeInspeccion.Estado, EstadoDelActaDeInspeccion.Registrada);

        // 1c. Eventos de otros contextos que el comando requiere (D5): si no han llegado para su identidad, 409.
        var reservaConfirmada = memoria.Buscar<ReservaConfirmada>("Reserva confirmada", actaDeInspeccion.NumeroDelArriendo)
            ?? throw new FaltaEventoRequerido("Determinar las diferencias entre entrega y devolución", "Reserva confirmada", actaDeInspeccion.NumeroDelArriendo);

        // 1d. Otras raíces que el comando lee (G6), por el dato con el nombre de su identidad; 404 si no existen.
        var actaDeEntrega = repositorioActaDeEntrega.Obtener(actaDeInspeccion.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe acta de entrega {actaDeInspeccion.NumeroDelArriendo}.");

        // 4. Reglas del contrato (archivo manual).
        var datos = new DeterminarLasDiferenciasEntreEntregaYDevolucionDatos(comando, actaDeInspeccion, reservaConfirmada, actaDeEntrega);
        ValidarReglas(datos);

        // 6. El comando solo lee la raíz: no guarda.

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new DiferenciasDeterminadas(actaDeInspeccion.NumeroDelArriendo, CombustibleConsumido(datos), HorasAdicionales(datos), ValorDeLosDanos(datos)), eventos);
        return new RespuestaDeComando(actaDeInspeccion.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
