// Generado desde ArchiMate: Model "YateGear" (id-98e02fd4df1c4f21a8610d291649a7af).
// Bus entre contextos (D1). No sale del modelo: es infraestructura. Los eventos viajan por su nombre en el
// modelo y en JSON, así que ningún contexto necesita las clases de otro. No editar: el generador reescribe
// este archivo.
#nullable enable
using System.Text.Json;
using System.Text.Json.Serialization;

namespace YateGear.Integracion;

/// <summary>Opciones de JSON comunes a los endpoints y al bus: nombres en camelCase y enums como texto.</summary>
public static class Json
{
    /// <summary>Opciones para leer y escribir eventos.</summary>
    public static JsonSerializerOptions Opciones { get; } = Configurar(new JsonSerializerOptions(JsonSerializerDefaults.Web));

    /// <summary>Agrega a unas opciones lo que necesitan los eventos (enums como texto).</summary>
    public static JsonSerializerOptions Configurar(JsonSerializerOptions opciones)
    {
        opciones.Converters.Add(new JsonStringEnumConverter());
        return opciones;
    }
}

/// <summary>Un evento que pasó por el bus entre contextos.</summary>
public sealed record EventoEntreContextos(int Orden, string Contexto, string Evento, string Identidad, JsonElement Datos);

/// <summary>Bus entre contextos, en memoria y síncrono. Cada contexto publica aquí sus eventos, y un contexto
/// se suscribe a un evento por su nombre. Si un suscriptor falla, el error queda en el historial y no deshace
/// el comando que publicó el evento, porque el evento ya ocurrió.</summary>
public sealed class BusEntreContextos
{
    private readonly Dictionary<string, List<Action<EventoEntreContextos>>> suscriptores = new();
    private readonly List<EventoEntreContextos> historial = new();
    private readonly List<string> errores = new();
    private readonly object candado = new();

    /// <summary>Suscribe una acción al evento con ese nombre en el modelo.</summary>
    public void Suscribir(string evento, Action<EventoEntreContextos> accion)
    {
        lock (candado)
        {
            if (!suscriptores.TryGetValue(evento, out var lista))
            {
                lista = new List<Action<EventoEntreContextos>>();
                suscriptores[evento] = lista;
            }
            lista.Add(accion);
        }
    }

    /// <summary>Publica un evento de un contexto: lo pasa a JSON, lo anota y llama a sus suscriptores.</summary>
    public void Publicar(string contexto, string evento, string identidad, object datos)
    {
        EventoEntreContextos mensaje;
        List<Action<EventoEntreContextos>> lista;
        lock (candado)
        {
            mensaje = new EventoEntreContextos(historial.Count + 1, contexto, evento, identidad,
                JsonSerializer.SerializeToElement(datos, datos.GetType(), Json.Opciones));
            historial.Add(mensaje);
            lista = suscriptores.TryGetValue(evento, out var s) ? s.ToList() : [];
        }
        foreach (var suscriptor in lista)
        {
            try
            {
                suscriptor(mensaje);
            }
            catch (Exception e)
            {
                lock (candado)
                {
                    errores.Add($"{mensaje.Orden} {evento}: {e.Message}");
                }
            }
        }
    }

    /// <summary>Los eventos que pasaron por el bus y los errores de los suscriptores, en orden.</summary>
    public object Historial()
    {
        lock (candado)
        {
            return new { eventos = historial.ToList(), errores = errores.ToList() };
        }
    }
}
