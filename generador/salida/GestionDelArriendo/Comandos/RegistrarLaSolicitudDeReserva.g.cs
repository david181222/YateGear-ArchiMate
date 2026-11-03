// Generado desde ArchiMate: ApplicationProcess "Registrar la solicitud de reserva" (SB-06, id-9995aadff41a4a86b109d51b13dbc11c).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en RegistrarLaSolicitudDeReserva.cs.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada del comando "Registrar la solicitud de reserva" (SB-06).</summary>
public sealed record RegistrarLaSolicitudDeReserva(
    string Cliente,
    string IdentificadorDelYate,
    string Propietario,
    decimal PrecioPorDia,
    string Marina,
    DateOnly Inicio,
    DateOnly Fin,
    string NumeroDeLaLicencia,
    DateOnly VigenciaDeLaLicencia,
    DateOnly FechaDeLaAutorizacion,
    List<string> TercerosAutorizados
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando y las respuestas de los servicios SA.</summary>
public sealed record RegistrarLaSolicitudDeReservaDatos(
    RegistrarLaSolicitudDeReserva Comando,
    ClientesDelCRMSalida ClientesDelCRM
);

/// <summary>Manejador del comando "Registrar la solicitud de reserva" (SB-06).</summary>
/// <remarks>
/// <para>Contrato de servicio: Registrar la solicitud de reserva (id-465c846ee8c64d42b5f2fc36cf376cd9), asociado al servicio de negocio
/// "Registrar la solicitud de reserva" (id-fdf9187711c74c839debc996243948f7), que el comando realiza.</para>
/// <para>Entrada: Cliente, yate, fecha de inicio, fecha de fin, licencia de navegación (número y vigencia) y autorización para el tratamiento de datos.</para>
/// <para>Salida: Arriendo con su número, en estado reserva solicitada, y ficha del cliente actualizada.</para>
/// <para>Reglas: el contrato no tiene reglas. Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class RegistrarLaSolicitudDeReservaManejador(
    Repositorio<Arriendo> repositorio,
    BusDeEventos bus,
    IClientesDelCRM clientesDelCRM
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(RegistrarLaSolicitudDeReservaDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(RegistrarLaSolicitudDeReserva comando)
    {
        // 1. El comando crea la raíz: se arma en el paso 6, después de ValidarReglas.

        // 2. Servicios SA que usa, en orden.
        var respuestaClientesDelCRM = clientesDelCRM.Llamar(new ClientesDelCRMEntrada(comando.Cliente, comando.IdentificadorDelYate, comando.Inicio, comando.Fin));

        // 4. Reglas del contrato (archivo manual).
        var datos = new RegistrarLaSolicitudDeReservaDatos(comando, respuestaClientesDelCRM);
        ValidarReglas(datos);

        // 6. Crear la raíz con su estado inicial y lo que guarda el comando. Al guardarla recibe su identidad.
        var arriendo = new Arriendo
        {
            Estado = EstadoDelArriendo.ReservaSolicitada,
            FechasDelArriendo = new FechasDelArriendo(comando.Inicio, comando.Fin),
            YateDelArriendo = new YateDelArriendo(comando.IdentificadorDelYate, comando.Propietario, comando.PrecioPorDia, comando.Marina),
            FichaDelCliente = new FichaDelCliente(respuestaClientesDelCRM.ReferenciaAlCRM, comando.NumeroDeLaLicencia, comando.VigenciaDeLaLicencia, comando.FechaDeLaAutorizacion, comando.TercerosAutorizados),
        };
        repositorio.Guardar(arriendo);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        Publicar(new ReservaSolicitada(arriendo.NumeroDelArriendo, comando.IdentificadorDelYate, comando.Inicio, comando.Fin), eventos);
        return new RespuestaDeComando(arriendo.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
