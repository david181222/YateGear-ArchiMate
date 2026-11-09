// Generado desde ArchiMate: ApplicationComponent "Contexto Gestión del arriendo" (id-fdcc9b19f08a492f8ccd5dd4559926bc).
// Infraestructura del piloto. No sale del modelo: repositorio en memoria, bus de eventos,
// bitácora y errores. No editar: el generador reescribe este archivo.
#nullable enable
using System.Globalization;
using System.Text.Json;
using YateGear.Integracion;

namespace YateGear.GestionDelArriendo;

/// <summary>Raíz de un agregado: tiene identidad, y el repositorio se la asigna al guardarla.</summary>
public interface IRaiz
{
    /// <summary>Identidad de la raíz; vacía hasta que se guarda por primera vez.</summary>
    string Identidad { get; }

    /// <summary>La usa el repositorio para asignar el consecutivo.</summary>
    void AsignarIdentidad(string identidad);
}

/// <summary>Entidad con identidad propia dentro de una raíz (G9). La raíz la guarda en una lista y no admite dos con
/// la misma identidad.</summary>
public interface IEntidad
{
    /// <summary>Identidad de la entidad dentro de su raíz.</summary>
    string Identidad { get; }
}

/// <summary>Operaciones sobre las listas de entidades de una raíz (G9).</summary>
public static class Entidades
{
    /// <summary>Agrega la entidad. Si la lista ya tiene una con la misma identidad, IdentidadRepetida (409).</summary>
    public static void Agregar<T>(List<T> lista, T entidad) where T : IEntidad
    {
        if (lista.Any(e => e.Identidad == entidad.Identidad))
        {
            throw new IdentidadRepetida(entidad.Identidad);
        }
        lista.Add(entidad);
    }
}

/// <summary>Evento del contexto.</summary>
public interface IEvento
{
    /// <summary>Nombre del evento en el modelo ArchiMate.</summary>
    string NombreEnElModelo { get; }

    /// <summary>Identidad de la raíz que publicó el evento.</summary>
    string Identidad { get; }
}

/// <summary>Repositorio en memoria de una raíz. Si la identidad es un consecutivo, lo asigna al guardar una raíz
/// nueva; si se forma con datos, la raíz nueva se agrega con su identidad.</summary>
public sealed class Repositorio<T>(string prefijo = "", int digitos = 0) where T : class, IRaiz
{
    private readonly Dictionary<string, T> raices = new();
    private readonly object candado = new();
    private int ultimo;

    /// <summary>La raíz con esa identidad, o null si no existe.</summary>
    public T? Obtener(string identidad)
    {
        lock (candado)
        {
            return raices.GetValueOrDefault(identidad);
        }
    }

    /// <summary>Una raíz nueva que todavía no se guarda, con su identidad (crea: si_no_existe). Se guarda con Guardar.</summary>
    public static T ConIdentidad(T raiz, string identidad)
    {
        raiz.AsignarIdentidad(identidad);
        return raiz;
    }

    /// <summary>Todas las raíces, en el orden en que se agregaron.</summary>
    public IReadOnlyList<T> Todas()
    {
        lock (candado)
        {
            return raices.Values.ToList();
        }
    }

    /// <summary>Agrega una raíz nueva con su identidad (formada con datos). Si ya existe, IdentidadRepetida (409).</summary>
    public void Agregar(T raiz, string identidad)
    {
        lock (candado)
        {
            if (raices.ContainsKey(identidad))
            {
                throw new IdentidadRepetida(identidad);
            }
            raiz.AsignarIdentidad(identidad);
            raices[identidad] = raiz;
        }
    }

    /// <summary>Guarda la raíz. Si es nueva, le asigna el siguiente consecutivo (por ejemplo {prefijo}0001).</summary>
    public void Guardar(T raiz)
    {
        lock (candado)
        {
            if (raiz.Identidad.Length == 0)
            {
                ultimo++;
                raiz.AsignarIdentidad(prefijo + ultimo.ToString("D" + digitos, CultureInfo.InvariantCulture));
            }
            raices[raiz.Identidad] = raiz;
        }
    }
}

/// <summary>Registro en orden de lo que pasa: eventos publicados y llamadas a los servicios SA simulados.</summary>
public sealed class Bitacora
{
    private readonly List<RegistroDeBitacora> registros = new();
    private readonly object candado = new();

    /// <summary>Agrega un registro al final.</summary>
    public void Anotar(string tipo, string nombre, object? datos)
    {
        lock (candado)
        {
            registros.Add(new RegistroDeBitacora(registros.Count + 1, tipo, nombre, datos));
        }
    }

    /// <summary>Todos los registros, en orden.</summary>
    public IReadOnlyList<RegistroDeBitacora> Todo()
    {
        lock (candado)
        {
            return registros.ToList();
        }
    }
}

/// <summary>Un registro de la bitácora.</summary>
public sealed record RegistroDeBitacora(int Orden, string Tipo, string Nombre, object? Datos);

/// <summary>Bus de eventos del contexto, en memoria y síncrono. Cada evento se publica también en el bus entre
/// contextos, por nombre y en JSON (D1). Si un suscriptor falla, el error queda en la bitácora y no deshace el
/// comando que publicó el evento, porque el evento ya ocurrió.</summary>
public sealed class BusDeEventos(Bitacora bitacora, BusEntreContextos entreContextos, string contexto)
{
    private readonly Dictionary<Type, List<Action<IEvento>>> suscriptores = new();

    /// <summary>Suscribe una acción a un tipo de evento.</summary>
    public void Suscribir<TEvento>(Action<TEvento> accion) where TEvento : IEvento
    {
        if (!suscriptores.TryGetValue(typeof(TEvento), out var lista))
        {
            lista = new List<Action<IEvento>>();
            suscriptores[typeof(TEvento)] = lista;
        }
        lista.Add(e => accion((TEvento)e));
    }

    /// <summary>Anota el evento en la bitácora y llama a sus suscriptores.</summary>
    public void Publicar(IEvento evento)
    {
        bitacora.Anotar("evento", evento.NombreEnElModelo, evento);
        entreContextos.Publicar(contexto, evento.NombreEnElModelo, evento.Identidad, evento);
        if (!suscriptores.TryGetValue(evento.GetType(), out var lista))
        {
            return;
        }
        foreach (var suscriptor in lista)
        {
            try
            {
                suscriptor(evento);
            }
            catch (Exception e)
            {
                bitacora.Anotar("error en política", evento.NombreEnElModelo, e.Message);
            }
        }
    }
}

/// <summary>Respuesta de un comando: la identidad de la raíz y los eventos que publicó.</summary>
public sealed record RespuestaDeComando(string Identidad, IReadOnlyList<string> Eventos)
{
    /// <summary>Junta las respuestas de varios comandos disparados por lo mismo (un evento o un mensaje): la identidad
    /// del primero que corrió (o la que se da, si no corrió ninguno) y todos los eventos, en orden.</summary>
    public static RespuestaDeComando Juntar(string identidad, IReadOnlyList<RespuestaDeComando> respuestas) =>
        new(respuestas.Count > 0 ? respuestas[0].Identidad : identidad, respuestas.SelectMany(r => r.Eventos).ToList());
}

/// <summary>Se incumplió una regla del contrato. Responde 422.</summary>
public sealed class ReglaIncumplida(string regla, string motivo) : Exception($"{regla}: {motivo}")
{
    /// <summary>Código de la regla en el modelo o en el contrato.</summary>
    public string Regla { get; } = regla;

    /// <summary>Por qué se rechazó.</summary>
    public string Motivo { get; } = motivo;
}

/// <summary>No existe la raíz pedida. Responde 404.</summary>
public sealed class NoEncontrado(string mensaje) : Exception(mensaje);

/// <summary>Ya existe una raíz con esa identidad (formada con datos). Responde 409.</summary>
public sealed class IdentidadRepetida(string identidad) : Exception($"Ya existe {identidad}.")
{
    /// <summary>La identidad repetida.</summary>
    public string Identidad { get; } = identidad;
}

/// <summary>Un evento de otro contexto que el comando requiere no ha llegado para esa identidad (requiere, D5).
/// Responde 409.</summary>
public sealed class FaltaEventoRequerido(string operacion, string evento, string identidad)
    : Exception($"\"{operacion}\" requiere \"{evento}\" de {identidad}, y no ha llegado.")
{
    /// <summary>Comando que se intentó.</summary>
    public string Operacion { get; } = operacion;

    /// <summary>Evento requerido.</summary>
    public string Evento { get; } = evento;

    /// <summary>Identidad con que se buscó.</summary>
    public string Identidad { get; } = identidad;
}

/// <summary>Falta un dato que la operación necesita. Responde 422.</summary>
public sealed class DatoFaltante(string dato) : Exception($"Falta el dato \"{dato}\".");

/// <summary>La operación no se permite en el estado actual de la raíz (capa 2). Responde 409.</summary>
public sealed class TransicionInvalida(string operacion, string estadoActual, IReadOnlyList<string> permitidos)
    : Exception($"\"{operacion}\" no se permite en el estado {estadoActual}.")
{
    /// <summary>Comando, o comando y resultado, que se intentó.</summary>
    public string Operacion { get; } = operacion;

    /// <summary>Estado en que estaba la raíz.</summary>
    public string EstadoActual { get; } = estadoActual;

    /// <summary>Estados desde los que sí se permite (desde del YAML).</summary>
    public IReadOnlyList<string> Permitidos { get; } = permitidos;
}

/// <summary>Revisión de estados (capa 2).</summary>
public static class Estados
{
    /// <summary>Lanza TransicionInvalida si el estado actual no está entre los permitidos.</summary>
    public static void Exigir<TEstado>(string operacion, TEstado actual, params TEstado[] permitidos) where TEstado : struct, Enum
    {
        if (Array.IndexOf(permitidos, actual) < 0)
        {
            throw new TransicionInvalida(operacion, actual.ToString(), permitidos.Select(p => p.ToString()).ToList());
        }
    }
}

/// <summary>Eventos que deben llegar juntos para disparar un comando: los de otros contextos (junto_con, capa 3) y los
/// de las políticas internas con varios disparos (junto_con y uno_de, G10). Los que ya llegaron se guardan en
/// memoria por la identidad de la raíz.</summary>
public sealed class EsperaDeEventos
{
    private readonly Dictionary<string, Dictionary<string, IEvento>> llegados = new();
    private readonly object candado = new();

    /// <summary>Anota el evento. Si ya llegaron todos los del grupo para esa identidad (y, si hay unoDe, al menos uno de
    /// esos), los devuelve y los quita de la espera; si no, devuelve null y en faltan los que todavía no llegan.</summary>
    public IReadOnlyDictionary<string, IEvento>? Anotar(string grupo, IReadOnlyList<string> eventosDelGrupo, IEvento evento,
        out IReadOnlyList<string> faltan, IReadOnlyList<string>? unoDe = null)
    {
        lock (candado)
        {
            var clave = grupo + "|" + evento.Identidad;
            if (!llegados.TryGetValue(clave, out var ya))
            {
                ya = new Dictionary<string, IEvento>();
                llegados[clave] = ya;
            }
            ya[evento.NombreEnElModelo] = evento;
            var lista = eventosDelGrupo.Where(n => !ya.ContainsKey(n)).ToList();
            if (unoDe is { Count: > 0 } && !unoDe.Any(ya.ContainsKey))
            {
                lista.Add("uno de: " + string.Join(", ", unoDe));
            }
            faltan = lista;
            if (faltan.Count > 0)
            {
                return null;
            }
            llegados.Remove(clave);
            return ya;
        }
    }
}

/// <summary>Eventos de otros contextos que algún comando requiere (requiere, D5). Se guardan en memoria por su
/// nombre y su identidad; si llega otro igual, reemplaza al anterior.</summary>
public sealed class MemoriaDeEventos
{
    private readonly Dictionary<string, IEvento> eventos = new();
    private readonly object candado = new();

    /// <summary>Recuerda el evento.</summary>
    public void Anotar(IEvento evento)
    {
        lock (candado)
        {
            eventos[evento.NombreEnElModelo + "|" + evento.Identidad] = evento;
        }
    }

    /// <summary>El evento con ese nombre e identidad, o null si no ha llegado.</summary>
    public T? Buscar<T>(string nombre, string identidad) where T : class, IEvento
    {
        lock (candado)
        {
            return eventos.GetValueOrDefault(nombre + "|" + identidad) as T;
        }
    }
}

/// <summary>Lee un evento de otro contexto desde JSON. Si falta un dato obligatorio (o llega en null), lanza
/// DatoFaltante con su nombre en el modelo, en vez de dejarlo vacío (D1: así se nota si el contexto que publica
/// lo llama distinto, D2).</summary>
public static class LectorDeEventos
{
    /// <summary>Revisa los datos obligatorios (nombre en JSON y nombre en el modelo) y lee el evento.</summary>
    public static T Leer<T>(JsonElement json, params (string Propiedad, string Dato)[] obligatorios)
    {
        if (json.ValueKind != JsonValueKind.Object)
        {
            throw new DatoFaltante("evento");
        }
        foreach (var (propiedad, dato) in obligatorios)
        {
            var viene = json.EnumerateObject().Any(p =>
                string.Equals(p.Name, propiedad, StringComparison.OrdinalIgnoreCase) && p.Value.ValueKind != JsonValueKind.Null);
            if (!viene)
            {
                throw new DatoFaltante(dato);
            }
        }
        return json.Deserialize<T>(Json.Opciones) ?? throw new DatoFaltante("evento");
    }
}

/// <summary>Respuesta a un evento de otro contexto: "esperando" (faltan eventos de su grupo, responde 202),
/// "ejecutado" (disparó su comando) o "recordado" (solo se guardó, para los comandos que lo requieren).</summary>
public sealed record RespuestaDeEventoExterno(string Estado, IReadOnlyList<string> Faltan, RespuestaDeComando? Comando)
{
    /// <summary>Faltan eventos del grupo junto_con.</summary>
    public static RespuestaDeEventoExterno Esperando(IReadOnlyList<string> faltan) => new("esperando", faltan, null);

    /// <summary>El evento disparó su comando.</summary>
    public static RespuestaDeEventoExterno Ejecutado(RespuestaDeComando comando) => new("ejecutado", [], comando);

    /// <summary>El evento solo se recordó.</summary>
    public static RespuestaDeEventoExterno Recordado() => new("recordado", [], null);
}
