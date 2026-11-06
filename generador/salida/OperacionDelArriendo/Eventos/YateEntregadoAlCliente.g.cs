// Generado desde ArchiMate: ApplicationEvent "Yate entregado al cliente" (id-275970c646a74ac3ac7c206246d780ab).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Evento "Yate entregado al cliente". Lo publica "Registrar el acta de entrega" (SB-22).</summary>
public sealed record YateEntregadoAlCliente(
    string NumeroDelArriendo,
    string IdentificadorDelYate,
    DateTime HoraDeEntrega
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Yate entregado al cliente";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
