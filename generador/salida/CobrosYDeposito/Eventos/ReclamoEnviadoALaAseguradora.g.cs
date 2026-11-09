// Generado desde ArchiMate: ApplicationEvent "Reclamo enviado a la aseguradora" (id-b13f9d27ed8d4bdd8d84224b82a64673).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Reclamo enviado a la aseguradora". Lo publica "Reclamar el excedente de daños a la aseguradora" (SB-16).</summary>
public sealed record ReclamoEnviadoALaAseguradora(
    string NumeroDeReclamo,
    string IdentificadorDelArriendo,
    decimal ValorQueExcedeElDeposito,
    string Numero,
    EstadoDelReclamoEnLaAseguradora? EstadoDelReclamo
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Reclamo enviado a la aseguradora";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDeReclamo;
}
