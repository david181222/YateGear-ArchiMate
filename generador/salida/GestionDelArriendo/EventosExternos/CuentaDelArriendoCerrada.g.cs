// Generado desde ArchiMate: ApplicationEvent "Cuenta del arriendo cerrada" (id-d853efb4ccfe4d5c9b75522348b303df).
// Evento de otro contexto (Contexto Cobros y depósito) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Cuenta del arriendo cerrada" de "Contexto Cobros y depósito", con los datos que declara el YAML. Dispara "Registrar el avance del arriendo".</summary>
public sealed record CuentaDelArriendoCerrada(
    string NumeroDelArriendo,
    DateTime HoraDelCierre
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Cuenta del arriendo cerrada";

    /// <summary>Identidad con que llega el evento: número del arriendo.</summary>
    public string Identidad => NumeroDelArriendo;
}
