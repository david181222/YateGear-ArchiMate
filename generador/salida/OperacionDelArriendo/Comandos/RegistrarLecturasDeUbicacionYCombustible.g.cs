// Generado desde ArchiMate: ApplicationProcess "Registrar lecturas de ubicación y combustible" (SB-25, id-9fe7bd3168374a12ac9efc3a073f62c9).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en RegistrarLecturasDeUbicacionYCombustible.cs.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Entrada del comando "Registrar lecturas de ubicación y combustible" (SB-25).</summary>
public sealed record RegistrarLecturasDeUbicacionYCombustible(
    string IdentificadorDelYate,
    decimal Latitud,
    decimal Longitud,
    decimal NivelDeCombustible,
    DateTime HoraDeLaLectura
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record RegistrarLecturasDeUbicacionYCombustibleDatos(
    RegistrarLecturasDeUbicacionYCombustible Comando
);

/// <summary>Manejador del comando "Registrar lecturas de ubicación y combustible" (SB-25).</summary>
/// <remarks>
/// <para>Contrato de servicio: Registrar lecturas de ubicación y combustible (id-d1c1c856cfdd44eca9b14a72b19166b1), asociado al servicio de negocio
/// "Registrar lecturas de ubicación y combustible" (id-7de936d1233146b7bd0f868b6b19001f), que el comando realiza.</para>
/// <para>Entrada: Yate, posición, nivel de combustible y hora de la lectura.</para>
/// <para>Salida: Lectura guardada.</para>
/// <para>Reglas: el contrato no tiene reglas. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class RegistrarLecturasDeUbicacionYCombustibleManejador(
    Repositorio<LecturaDeUbicacionYCombustible> repositorio,
    BusDeEventos bus
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(RegistrarLecturasDeUbicacionYCombustibleDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(RegistrarLecturasDeUbicacionYCombustible comando)
    {
        if (string.IsNullOrEmpty(comando.IdentificadorDelYate)) throw new DatoFaltante("identificador del yate");
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 4. Reglas del contrato (archivo manual).
        var datos = new RegistrarLecturasDeUbicacionYCombustibleDatos(comando);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Su identidad se forma con datos;
        //    si ya existe una raíz con esa identidad, 409.
        var lecturaDeUbicacionYCombustible = new LecturaDeUbicacionYCombustible
        {
            Estado = EstadoDeLaLectura.Registrada,
            Latitud = comando.Latitud,
            Longitud = comando.Longitud,
            NivelDeCombustible = comando.NivelDeCombustible,
            HoraDeLaLectura = comando.HoraDeLaLectura,
            IdentificadorDelYate = comando.IdentificadorDelYate,
        };
        repositorio.Agregar(lecturaDeUbicacionYCombustible, $"{(comando.IdentificadorDelYate)}/{((comando.HoraDeLaLectura).ToString("s", System.Globalization.CultureInfo.InvariantCulture))}");

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new LecturaRegistrada(lecturaDeUbicacionYCombustible.IdentificadorDeLaLectura, comando.IdentificadorDelYate, comando.HoraDeLaLectura), eventos);
        return new RespuestaDeComando(lecturaDeUbicacionYCombustible.IdentificadorDeLaLectura, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
