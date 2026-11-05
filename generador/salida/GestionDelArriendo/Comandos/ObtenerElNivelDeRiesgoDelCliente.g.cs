// Generado desde ArchiMate: ApplicationProcess "Obtener el nivel de riesgo del cliente" (SB-12, id-2a55b3149f0d4388ba3551743aa65cf4).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en ObtenerElNivelDeRiesgoDelCliente.cs.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada del comando "Obtener el nivel de riesgo del cliente" (SB-12).</summary>
public sealed record ObtenerElNivelDeRiesgoDelCliente(
    string NumeroDelArriendo
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: el comando, la raíz y las respuestas de los servicios SA.</summary>
public sealed record ObtenerElNivelDeRiesgoDelClienteDatos(
    ObtenerElNivelDeRiesgoDelCliente Comando,
    Arriendo Arriendo,
    NivelDeRiesgoDeLaEvaluadoraSalida NivelDeRiesgoDeLaEvaluadora,
    ObtenerElNivelDeRiesgoDelClienteResultado Resultado
);

/// <summary>Resultados de "Obtener el nivel de riesgo del cliente": un evento por resultado.</summary>
public enum ObtenerElNivelDeRiesgoDelClienteResultado
{
    /// <summary>Publica "Riesgo aceptable obtenido".</summary>
    RiesgoAceptableObtenido,
    /// <summary>Publica "Arriendo no realizado por riesgo alto".</summary>
    ArriendoNoRealizadoPorRiesgoAlto,
}

/// <summary>Manejador del comando "Obtener el nivel de riesgo del cliente" (SB-12).</summary>
/// <remarks>
/// <para>Contrato de servicio: Obtener el nivel de riesgo del cliente (id-3f0507fda0fa42ecb67a0f2e7864f30e), asociado al servicio de negocio
/// "Obtener el nivel de riesgo del cliente" (id-fd6888a3bfcc449a982901555851cbcb), que el comando realiza.</para>
/// <para>Entrada: Arriendo y datos del cliente que autorizó compartir.</para>
/// <para>Salida: Nivel de riesgo (bajo, medio o alto) y decisión: aceptable o no se arrienda.</para>
/// <para>Reglas: Con riesgo alto el arriendo no se realiza (REG-01); aceptable es bajo o medio (V4-SUP-02). No se envían datos a la evaluadora sin la autorización del cliente (H-19). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class ObtenerElNivelDeRiesgoDelClienteManejador(
    Repositorio<Arriendo> repositorio,
    BusDeEventos bus,
    INivelDeRiesgoDeLaEvaluadora nivelDeRiesgoDeLaEvaluadora
)
{
    /// <summary>Reglas del contrato que no son transiciones de estado. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(ObtenerElNivelDeRiesgoDelClienteDatos datos);

    /// <summary>Ejecuta el comando.</summary>
    public RespuestaDeComando Manejar(ObtenerElNivelDeRiesgoDelCliente comando)
    {
        if (string.IsNullOrEmpty(comando.NumeroDelArriendo)) throw new DatoFaltante("número del arriendo");
        // 1. Cargar la raíz.
        var arriendo = repositorio.Obtener(comando.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe arriendo {comando.NumeroDelArriendo}.");

        // 1b. Estados desde los que se permite el comando (capa 2), antes de llamar a los SA.
        Estados.Exigir("Obtener el nivel de riesgo del cliente", arriendo.Estado, EstadoDelArriendo.ReservaSolicitada);

        // 2. Servicios SA que usa, en orden.
        var respuestaNivelDeRiesgoDeLaEvaluadora = nivelDeRiesgoDeLaEvaluadora.Llamar(new NivelDeRiesgoDeLaEvaluadoraEntrada(arriendo.FichaDelCliente.ReferenciaAlCRM));

        // 3. Elegir el resultado (condición si del YAML).
        var resultado =
            (respuestaNivelDeRiesgoDeLaEvaluadora.Nivel == NivelDeRiesgo.Bajo || respuestaNivelDeRiesgoDeLaEvaluadora.Nivel == NivelDeRiesgo.Medio) ? ObtenerElNivelDeRiesgoDelClienteResultado.RiesgoAceptableObtenido :
            (respuestaNivelDeRiesgoDeLaEvaluadora.Nivel == NivelDeRiesgo.Alto) ? ObtenerElNivelDeRiesgoDelClienteResultado.ArriendoNoRealizadoPorRiesgoAlto :
            throw new ReglaIncumplida("resultados", "Ningún resultado de \"Obtener el nivel de riesgo del cliente\" se cumple con estos datos.");

        // 4. Reglas del contrato (archivo manual).
        var datos = new ObtenerElNivelDeRiesgoDelClienteDatos(comando, arriendo, respuestaNivelDeRiesgoDeLaEvaluadora, resultado);
        ValidarReglas(datos);

        // 6. Guardar en la raíz lo que escribe el comando y su nuevo estado (capa 2).
        arriendo.EvaluacionDeRiesgo = new EvaluacionDeRiesgo(respuestaNivelDeRiesgoDeLaEvaluadora.Nivel, respuestaNivelDeRiesgoDeLaEvaluadora.Fecha);
        switch (resultado)
        {
            case ObtenerElNivelDeRiesgoDelClienteResultado.ArriendoNoRealizadoPorRiesgoAlto:
                arriendo.Estado = EstadoDelArriendo.NoRealizadoPorRiesgoAlto;
                break;
        }
        repositorio.Guardar(arriendo);

        // 7. Publicar los eventos.
        var eventos = new List<string>();
        switch (resultado)
        {
            case ObtenerElNivelDeRiesgoDelClienteResultado.RiesgoAceptableObtenido:
                Publicar(new RiesgoAceptableObtenido(arriendo.NumeroDelArriendo, arriendo.FichaDelCliente.ReferenciaAlCRM, arriendo.YateDelArriendo.IdentificadorDelYate, arriendo.FechasDelArriendo.Inicio, arriendo.FechasDelArriendo.Fin, arriendo.YateDelArriendo.PrecioPorDia), eventos);
                break;
            case ObtenerElNivelDeRiesgoDelClienteResultado.ArriendoNoRealizadoPorRiesgoAlto:
                Publicar(new ArriendoNoRealizadoPorRiesgoAlto(arriendo.NumeroDelArriendo, arriendo.YateDelArriendo.IdentificadorDelYate, arriendo.FechasDelArriendo.Inicio, arriendo.FechasDelArriendo.Fin), eventos);
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
