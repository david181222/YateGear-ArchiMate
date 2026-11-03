// Generado desde ArchiMate: ApplicationEvent "Inspección de devolución registrada" (id-d83f5b5cfb764e7aaac782ffab1b12c4).
// Evento de otro contexto (Contexto Operación del arriendo) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Inspección de devolución registrada" de "Contexto Operación del arriendo", con los datos que declara el YAML. Dispara "Registrar el avance del arriendo".</summary>
public sealed record InspeccionDeDevolucionRegistrada(
    string NumeroDelArriendo,
    DateTime FechaYHoraDelCambio
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Inspección de devolución registrada";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
