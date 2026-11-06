// Generado desde ArchiMate: ApplicationProcess "Registrar el avance del arriendo" (SB-09, id-5be75381f2364a9cb9fa8d4247dce743).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en RegistrarElAvanceDelArriendo.cs.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada del comando "Registrar el avance del arriendo" (SB-09).</summary>
public sealed record RegistrarElAvanceDelArriendo(
    string NumeroDelArriendo,
    AvanceDelArriendo NuevoEstado,
    DateTime FechaYHoraDelCambio
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record RegistrarElAvanceDelArriendoDatos(
    RegistrarElAvanceDelArriendo Comando,
    Arriendo Arriendo,
    RegistrarElAvanceDelArriendoResultado Resultado
);

/// <summary>Resultados de "Registrar el avance del arriendo": un evento por resultado.</summary>
public enum RegistrarElAvanceDelArriendoResultado
{
    /// <summary>Publica "Arriendo iniciado".</summary>
    ArriendoIniciado,
    /// <summary>Publica "Yate devuelto".</summary>
    YateDevuelto,
    /// <summary>Publica "Arriendo cerrado".</summary>
    ArriendoCerrado,
}

/// <summary>Manejador del comando "Registrar el avance del arriendo" (SB-09).</summary>
/// <remarks>
/// <para>Contrato de servicio: Registrar el avance del arriendo (id-c6439672662d41ea93ee102abbe217eb), asociado al servicio de negocio
/// "Registrar el avance del arriendo" (id-6ae0b61c65954576beacb7a29ff9af88), que el comando realiza.</para>
/// <para>Entrada: Arriendo, nuevo estado y fecha y hora del cambio.</para>
/// <para>Salida: Arriendo con el estado actualizado.</para>
/// <para>Reglas: Se rechaza cerrar el arriendo antes de terminar los ajustes de dinero, porque con ellos se cierra (E2E-01). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class RegistrarElAvanceDelArriendoManejador(
    Repositorio<Arriendo> repositorio,
    BusDeEventos bus
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(RegistrarElAvanceDelArriendoDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(RegistrarElAvanceDelArriendo comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. Cargar la raíz.
        var arriendo = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe arriendo {comando.NumeroDelArriendo}.");

        // 3. Elegir el resultado (condición si del YAML).
        var resultado =
            (comando.NuevoEstado == AvanceDelArriendo.EnCurso) ? RegistrarElAvanceDelArriendoResultado.ArriendoIniciado :
            (comando.NuevoEstado == AvanceDelArriendo.Devuelto) ? RegistrarElAvanceDelArriendoResultado.YateDevuelto :
            (comando.NuevoEstado == AvanceDelArriendo.Cerrado) ? RegistrarElAvanceDelArriendoResultado.ArriendoCerrado :
            throw new ReglaIncumplida("resultados", "Ningún resultado de \"Registrar el avance del arriendo\" se cumple con estos datos.");

        // Estados desde los que se permite el resultado elegido (capa 2).
        switch (resultado)
        {
            case RegistrarElAvanceDelArriendoResultado.ArriendoIniciado:
                Estados.Exigir("Registrar el avance del arriendo: Arriendo iniciado", arriendo.Estado, EstadoDelArriendo.ReservaConfirmada);
                break;
            case RegistrarElAvanceDelArriendoResultado.YateDevuelto:
                Estados.Exigir("Registrar el avance del arriendo: Yate devuelto", arriendo.Estado, EstadoDelArriendo.EnCurso);
                break;
            case RegistrarElAvanceDelArriendoResultado.ArriendoCerrado:
                Estados.Exigir("Registrar el avance del arriendo: Arriendo cerrado", arriendo.Estado, EstadoDelArriendo.Devuelto);
                break;
        }

        // 4. Reglas del contrato (archivo manual).
        var datos = new RegistrarElAvanceDelArriendoDatos(comando, arriendo, resultado);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        switch (resultado)
        {
            case RegistrarElAvanceDelArriendoResultado.ArriendoIniciado:
                arriendo.Estado = EstadoDelArriendo.EnCurso;
                break;
            case RegistrarElAvanceDelArriendoResultado.YateDevuelto:
                arriendo.Estado = EstadoDelArriendo.Devuelto;
                break;
            case RegistrarElAvanceDelArriendoResultado.ArriendoCerrado:
                arriendo.Estado = EstadoDelArriendo.Cerrado;
                break;
        }
        repositorio.Guardar(arriendo);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        switch (resultado)
        {
            case RegistrarElAvanceDelArriendoResultado.ArriendoIniciado:
                Publicar(new ArriendoIniciado(arriendo.NumeroDelArriendo, comando.FechaYHoraDelCambio), eventos);
                break;
            case RegistrarElAvanceDelArriendoResultado.YateDevuelto:
                Publicar(new YateDevuelto(arriendo.NumeroDelArriendo, comando.FechaYHoraDelCambio), eventos);
                break;
            case RegistrarElAvanceDelArriendoResultado.ArriendoCerrado:
                Publicar(new ArriendoCerrado(arriendo.NumeroDelArriendo, arriendo.FichaDelCliente.ReferenciaAlCRM, arriendo.YateDelArriendo.Propietario, comando.FechaYHoraDelCambio), eventos);
                break;
        }
        return new RespuestaDeComando(arriendo.NumeroDelArriendo, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
