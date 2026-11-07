// Generado desde ArchiMate: ApplicationEvent "Cuenta del arriendo cerrada" (id-d853efb4ccfe4d5c9b75522348b303df).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Cuenta del arriendo cerrada". Lo publica "Cerrar las cuentas del arriendo" (SB-17).</summary>
public sealed record CuentaDelArriendoCerrada(
    string NumeroDelArriendo,
    DateTime HoraDelCierre,
    string IdentificadorDelYate,
    string Propietario,
    decimal ValorDelAlquiler,
    decimal Comision,
    decimal ValorDelPropietario
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Cuenta del arriendo cerrada";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
