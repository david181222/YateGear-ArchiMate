// Generado desde ArchiMate: ApplicationEvent "Inspección de devolución registrada" (id-d83f5b5cfb764e7aaac782ffab1b12c4).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.OperacionDelArriendo;

/// <summary>Evento "Inspección de devolución registrada". Lo publica "Registrar la inspección de devolución" (SB-23).</summary>
public sealed record InspeccionDeDevolucionRegistrada(
    string NumeroDelArriendo,
    DateTime HoraDeRegreso
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Inspección de devolución registrada";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
