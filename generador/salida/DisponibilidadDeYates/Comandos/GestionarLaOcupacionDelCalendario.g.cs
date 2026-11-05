// Generado desde ArchiMate: ApplicationProcess "Gestionar la ocupación del calendario" (SB-05, id-91e23dd9dfb741b79a6f487952bd22c0).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en GestionarLaOcupacionDelCalendario.cs.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Entrada del comando "Gestionar la ocupación del calendario" (SB-05).</summary>
public sealed record GestionarLaOcupacionDelCalendario(
    string IdentificadorDelYate,
    DateOnly Inicio,
    DateOnly Fin,
    string NumeroDelArriendo,
    AccionSobreLaOcupacion Accion
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record GestionarLaOcupacionDelCalendarioDatos(
    GestionarLaOcupacionDelCalendario Comando,
    CalendarioDelYate CalendarioDelYate,
    GestionarLaOcupacionDelCalendarioResultado Resultado
);

/// <summary>Resultados de "Gestionar la ocupación del calendario": un evento por resultado.</summary>
public enum GestionarLaOcupacionDelCalendarioResultado
{
    /// <summary>Publica "Fechas apartadas".</summary>
    FechasApartadas,
    /// <summary>Publica "Fechas ocupadas".</summary>
    FechasOcupadas,
    /// <summary>Publica "Fechas liberadas".</summary>
    FechasLiberadas,
}

/// <summary>Manejador del comando "Gestionar la ocupación del calendario" (SB-05).</summary>
/// <remarks>
/// <para>Contrato de servicio: Gestionar la ocupación del calendario (id-683b3fd66779488b96a331df7112516d), asociado al servicio de negocio
/// "Gestionar la ocupación del calendario" (id-ad7eab80d09b41b2ba6afb14347e86f8), que el comando realiza.</para>
/// <para>Entrada: Yate, fechas, arriendo y acción: apartar, ocupar o soltar.</para>
/// <para>Salida: Calendario con las fechas apartadas, ocupadas o libres.</para>
/// <para>Reglas: Se rechaza apartar u ocupar fechas que ya tiene otro arriendo o que bloqueó el propietario: un yate no puede tener dos arriendos en las mismas fechas (REG-01). Las fechas se apartan al pedir la reserva y se ocupan al confirmarla (V4-SUP-01). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class GestionarLaOcupacionDelCalendarioManejador(
    Repositorio<CalendarioDelYate> repositorio,
    BusDeEventos bus
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(GestionarLaOcupacionDelCalendarioDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(GestionarLaOcupacionDelCalendario comando)
    {
        if (string.IsNullOrEmpty(comando.IdentificadorDelYate)) throw new DatoFaltante("identificador del yate");
        // 1. Cargar la raíz; si no existe, se crea vacía con la identidad del comando (crea: si_no_existe).
        //    Se guarda en el paso 6, así que una solicitud rechazada no la deja creada.
        var calendarioDelYate = repositorio.Obtener(comando.IdentificadorDelYate)
            ?? Repositorio<CalendarioDelYate>.ConIdentidad(new CalendarioDelYate { Estado = EstadoDelCalendario.Activo }, comando.IdentificadorDelYate);

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Gestionar la ocupación del calendario", calendarioDelYate.Estado, EstadoDelCalendario.Activo);

        // 3. Elegir el resultado (condición si del YAML).
        var resultado =
            (comando.Accion == AccionSobreLaOcupacion.Apartar) ? GestionarLaOcupacionDelCalendarioResultado.FechasApartadas :
            (comando.Accion == AccionSobreLaOcupacion.Ocupar) ? GestionarLaOcupacionDelCalendarioResultado.FechasOcupadas :
            (comando.Accion == AccionSobreLaOcupacion.Soltar) ? GestionarLaOcupacionDelCalendarioResultado.FechasLiberadas :
            throw new ReglaIncumplida("resultados", "Ningún resultado de \"Gestionar la ocupación del calendario\" se cumple con estos datos.");

        // 4. Reglas del contrato (archivo manual).
        var datos = new GestionarLaOcupacionDelCalendarioDatos(comando, calendarioDelYate, resultado);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        switch (resultado)
        {
            case GestionarLaOcupacionDelCalendarioResultado.FechasApartadas:
                calendarioDelYate.RangoDeFechas.Add(new RangoDeFechas(comando.Inicio, comando.Fin, EstadoDeLaFecha.Apartada, comando.NumeroDelArriendo));
                break;
            case GestionarLaOcupacionDelCalendarioResultado.FechasOcupadas:
                if (calendarioDelYate.RangoDeFechas.RemoveAll(e => e.NumeroDelArriendo == comando.NumeroDelArriendo) == 0) throw new NoEncontrado("No hay un \"Rango de fechas\" con ese número del arriendo.");
                calendarioDelYate.RangoDeFechas.Add(new RangoDeFechas(comando.Inicio, comando.Fin, EstadoDeLaFecha.Ocupada, comando.NumeroDelArriendo));
                break;
            case GestionarLaOcupacionDelCalendarioResultado.FechasLiberadas:
                calendarioDelYate.RangoDeFechas.RemoveAll(e => e.NumeroDelArriendo == comando.NumeroDelArriendo);
                break;
        }
        repositorio.Guardar(calendarioDelYate);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        switch (resultado)
        {
            case GestionarLaOcupacionDelCalendarioResultado.FechasApartadas:
                Publicar(new FechasApartadas(calendarioDelYate.IdentificadorDelYate, comando.NumeroDelArriendo, comando.Inicio, comando.Fin), eventos);
                break;
            case GestionarLaOcupacionDelCalendarioResultado.FechasOcupadas:
                Publicar(new FechasOcupadas(calendarioDelYate.IdentificadorDelYate, comando.NumeroDelArriendo, comando.Inicio, comando.Fin), eventos);
                break;
            case GestionarLaOcupacionDelCalendarioResultado.FechasLiberadas:
                Publicar(new FechasLiberadas(calendarioDelYate.IdentificadorDelYate, comando.NumeroDelArriendo, comando.Inicio, comando.Fin), eventos);
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
