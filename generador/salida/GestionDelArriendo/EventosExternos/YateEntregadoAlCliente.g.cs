// Generado desde ArchiMate: ApplicationEvent "Yate entregado al cliente" (id-275970c646a74ac3ac7c206246d780ab).
// Evento de otro contexto (Contexto Operación del arriendo) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Yate entregado al cliente" de "Contexto Operación del arriendo", con los datos que declara el YAML. Dispara "Registrar el avance del arriendo".</summary>
public sealed record YateEntregadoAlCliente(
    string NumeroDelArriendo,
    DateTime FechaYHoraDelCambio
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Yate entregado al cliente";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
