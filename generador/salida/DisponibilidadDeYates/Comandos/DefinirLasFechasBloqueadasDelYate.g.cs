// Generado desde ArchiMate: ApplicationProcess "Definir las fechas bloqueadas del yate" (SB-03, id-f4ce9e396faf4c5395d097ec91278ec2).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en DefinirLasFechasBloqueadasDelYate.cs.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Entrada del comando "Definir las fechas bloqueadas del yate" (SB-03).</summary>
public sealed record DefinirLasFechasBloqueadasDelYate(
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin,
    AccionSobreElBloqueo Accion
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record DefinirLasFechasBloqueadasDelYateDatos(
    DefinirLasFechasBloqueadasDelYate Comando,
    CalendarioDelYate CalendarioDelYate,
    DefinirLasFechasBloqueadasDelYateResultado Resultado
);

/// <summary>Resultados de "Definir las fechas bloqueadas del yate": un evento por resultado.</summary>
public enum DefinirLasFechasBloqueadasDelYateResultado
{
    /// <summary>Publica "Fechas bloqueadas".</summary>
    FechasBloqueadas,
    /// <summary>Publica "Fechas desbloqueadas".</summary>
    FechasDesbloqueadas,
}

/// <summary>Manejador del comando "Definir las fechas bloqueadas del yate" (SB-03).</summary>
/// <remarks>
/// <para>Contrato de servicio: Definir las fechas bloqueadas del yate (id-33c845069c4641b9ad2e9d7585624b70), asociado al servicio de negocio
/// "Definir las fechas bloqueadas del yate" (id-ca9597cf3052403c99ebbb59510f497b), que el comando realiza.</para>
/// <para>Entrada: Yate, fecha de inicio, fecha de fin y acción (bloquear o desbloquear).</para>
/// <para>Salida: Calendario del yate actualizado.</para>
/// <para>Reglas: Se rechaza si quien hace el cambio no es el propietario del yate (E2E-02). Se rechaza el bloqueo de fechas que ya tienen una reserva confirmada (REG-02). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class DefinirLasFechasBloqueadasDelYateManejador(
    Repositorio<CalendarioDelYate> repositorio,
    BusDeEventos bus
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(DefinirLasFechasBloqueadasDelYateDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(DefinirLasFechasBloqueadasDelYate comando)
    {
        if (string.IsNullOrEmpty(comando.IdentificadorDelYate)) throw new DatoFaltante("identificador del yate");
        // 1. Cargar la raíz; si no existe, se crea vacía con la identidad del comando (crea: si_no_existe).
        //    Se guarda en el paso 6, así que una solicitud rechazada no la deja creada.
        var calendarioDelYate = repositorio.Obtener(comando.IdentificadorDelYate)
            ?? Repositorio<CalendarioDelYate>.ConIdentidad(new CalendarioDelYate { Estado = EstadoDelCalendario.Activo }, comando.IdentificadorDelYate);

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Definir las fechas bloqueadas del yate", calendarioDelYate.Estado, EstadoDelCalendario.Activo);

        // 3. Elegir el resultado (condición si del YAML).
        var resultado =
            (comando.Accion == AccionSobreElBloqueo.Bloquear) ? DefinirLasFechasBloqueadasDelYateResultado.FechasBloqueadas :
            (comando.Accion == AccionSobreElBloqueo.Desbloquear) ? DefinirLasFechasBloqueadasDelYateResultado.FechasDesbloqueadas :
            throw new ReglaIncumplida("resultados", "Ningún resultado de \"Definir las fechas bloqueadas del yate\" se cumple con estos datos.");

        // 4. Reglas del contrato (archivo manual).
        var datos = new DefinirLasFechasBloqueadasDelYateDatos(comando, calendarioDelYate, resultado);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        switch (resultado)
        {
            case DefinirLasFechasBloqueadasDelYateResultado.FechasBloqueadas:
                calendarioDelYate.RangoDeFechas.Add(new RangoDeFechas(comando.Inicio, comando.Fin, EstadoDeLaFecha.Bloqueada, null));
                break;
            case DefinirLasFechasBloqueadasDelYateResultado.FechasDesbloqueadas:
                calendarioDelYate.RangoDeFechas.RemoveAll(e => e.Inicio == comando.Inicio && e.Fin == comando.Fin && e.EstadoDeLaFecha == EstadoDeLaFecha.Bloqueada);
                break;
        }
        repositorio.Guardar(calendarioDelYate);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        switch (resultado)
        {
            case DefinirLasFechasBloqueadasDelYateResultado.FechasBloqueadas:
                Publicar(new FechasBloqueadas(calendarioDelYate.IdentificadorDelYate, comando.Inicio, comando.Fin), eventos);
                break;
            case DefinirLasFechasBloqueadasDelYateResultado.FechasDesbloqueadas:
                Publicar(new FechasDesbloqueadas(calendarioDelYate.IdentificadorDelYate, comando.Inicio, comando.Fin), eventos);
                break;
        }
        return new RespuestaDeComando(calendarioDelYate.IdentificadorDelYate, eventos);
    }

    private void Publicar(IEvento evento, List<string> eventos)
    {
        bus.Publicar(evento);
        eventos.Add(evento.NombreEnElModelo);
    }
}
