// Generado desde ArchiMate: ApplicationEvent "Depósito bloqueado" (id-41585106baae43ab90ca920de78dc737).
// Evento de otro contexto (Contexto Cobros y depósito) tal como lo recibe este contexto (capa 3). No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Evento "Depósito bloqueado" de "Contexto Cobros y depósito", con los datos que declara el YAML. Dispara "Confirmar la reserva".</summary>
public sealed record DepositoBloqueado(
    string NumeroDelArriendo,
    string AutorizacionDelBloqueoDelDeposito
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Depósito bloqueado";

    /// <summary>Identidad con que llega el evento: número del arriendo.</summary>
    public string Identidad => NumeroDelArriendo;
}
