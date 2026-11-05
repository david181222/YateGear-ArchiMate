// Generado desde ArchiMate: ApplicationProcess "Registrar la inspección de devolución" (SB-23, id-c6f7cd3f402f41feb9d986570982815a).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en RegistrarLaInspeccionDeDevolucion.cs.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Entrada del comando "Registrar la inspección de devolución" (SB-23).</summary>
public sealed record RegistrarLaInspeccionDeDevolucion(
    string NumeroDelArriendo,
    List<string> Fotos,
    decimal NivelDeCombustible,
    DateTime HoraDeRegreso,
    List<DanoEncontrado> DanosEncontrados
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record RegistrarLaInspeccionDeDevolucionDatos(
    RegistrarLaInspeccionDeDevolucion Comando
);

/// <summary>Manejador del comando "Registrar la inspección de devolución" (SB-23).</summary>
/// <remarks>
/// <para>Contrato de servicio: Registrar la inspección de devolución (id-6c8c966e7a6248108baa667653bba6bb), asociado al servicio de negocio
/// "Registrar la inspección de devolución" (id-b40f995062f94787bb4b0e458236b79c), que el comando realiza.</para>
/// <para>Entrada: Arriendo, fotos, nivel de combustible, hora de regreso y daños encontrados con su valor.</para>
/// <para>Salida: Acta de inspección registrada.</para>
/// <para>Reglas: Se rechaza una inspección sin fotos (H-13). El valor de los daños llega con la inspección (V4-SUP-03). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class RegistrarLaInspeccionDeDevolucionManejador(
    Repositorio<ActaDeInspeccion> repositorio,
    BusDeEventos bus
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(RegistrarLaInspeccionDeDevolucionDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(RegistrarLaInspeccionDeDevolucion comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 4. Reglas del contrato (archivo manual).
        var datos = new RegistrarLaInspeccionDeDevolucionDatos(comando);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Su identidad se forma con datos;
        //    si ya existe una raíz con esa identidad, 409.
        var actaDeInspeccion = new ActaDeInspeccion
        {
            Estado = EstadoDelActaDeInspeccion.Registrada,
            Fotos = comando.Fotos,
            NivelDeCombustible = comando.NivelDeCombustible,
            HoraDeRegreso = comando.HoraDeRegreso,
            DanoEncontrado = [.. (comando.DanosEncontrados ?? [])],
        };
        repositorio.Agregar(actaDeInspeccion, $"{(comando.NumeroDelArriendo)}");

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new InspeccionDeDevolucionRegistrada(actaDeInspeccion.NumeroDelArriendo, comando.HoraDeRegreso), eventos);
        return new RespuestaDeComando(actaDeInspeccion.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
