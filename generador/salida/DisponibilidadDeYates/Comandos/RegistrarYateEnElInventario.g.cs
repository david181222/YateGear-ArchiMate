// Generado desde ArchiMate: ApplicationProcess "Registrar yate en el inventario" (SB-01, id-8e392207203f40b2b0a50bcbe62efc90).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en RegistrarYateEnElInventario.cs.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Entrada del comando "Registrar yate en el inventario" (SB-01).</summary>
public sealed record RegistrarYateEnElInventario(
    string Propietario,
    string IdentificadorDeLaMarina,
    string Nombre,
    string Matricula,
    int Capacidad,
    decimal PrecioPorDia,
    bool DocumentosAlDiaAnteLaDIMAR
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record RegistrarYateEnElInventarioDatos(
    RegistrarYateEnElInventario Comando,
    ContratosConPropietariosYClientesSalida ContratosConPropietariosYClientes
);

/// <summary>Manejador del comando "Registrar yate en el inventario" (SB-01).</summary>
/// <remarks>
/// <para>Contrato de servicio: Registrar yate en el inventario (id-431ca877f2e34dd2b6243038d1bb256f), asociado al servicio de negocio
/// "Registrar yate en el inventario" (id-60d66be6c035440b8fc779d9918f6ae0), que el comando realiza.</para>
/// <para>Entrada: Propietario, marina, datos del yate (nombre, matrícula y capacidad), precio por día, documentos ante la DIMAR al día y contrato firmado con el propietario.</para>
/// <para>Salida: Yate registrado con su identificador.</para>
/// <para>Reglas: Se rechaza si el propietario no tiene contrato firmado (INT-CON) o si los documentos del yate ante la DIMAR no están al día (NOR-01). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class RegistrarYateEnElInventarioManejador(
    Repositorio<Yate> repositorio,
    BusDeEventos bus,
    IContratosConPropietariosYClientes contratosConPropietariosYClientes
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(RegistrarYateEnElInventarioDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(RegistrarYateEnElInventario comando)
    {
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 2. Servicios SA que usa, en orden.
        var respuestaContratosConPropietariosYClientes = contratosConPropietariosYClientes.Llamar(new ContratosConPropietariosYClientesEntrada(comando.Propietario));

        // 4. Reglas del contrato (archivo manual).
        var datos = new RegistrarYateEnElInventarioDatos(comando, respuestaContratosConPropietariosYClientes);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Al guardarla recibe su identidad.
        var yate = new Yate
        {
            Estado = EstadoDelYate.Registrado,
            Propietario = comando.Propietario,
            IdentificadorDeLaMarina = comando.IdentificadorDeLaMarina,
            DatosDelYate = new DatosDelYate(comando.Nombre, comando.Matricula, comando.Capacidad),
            PrecioPorDia = comando.PrecioPorDia,
            DocumentosAlDiaAnteLaDIMAR = comando.DocumentosAlDiaAnteLaDIMAR,
            ReferenciaDelContratoDelPropietario = respuestaContratosConPropietariosYClientes.ReferenciaDelContratoDelPropietario,
        };
        repositorio.Guardar(yate);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new YateRegistrado(yate.IdentificadorDelYate, comando.IdentificadorDeLaMarina, comando.PrecioPorDia), eventos);
        return new RespuestaDeComando(yate.IdentificadorDelYate, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
