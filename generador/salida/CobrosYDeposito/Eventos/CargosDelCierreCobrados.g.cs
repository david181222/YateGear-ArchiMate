// Generado desde ArchiMate: ApplicationEvent "Cargos del cierre cobrados" (id-7a5f1d6d01b94f3ba9f0bc496545062f).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.CobrosYDeposito;

/// <summary>Evento "Cargos del cierre cobrados". Lo publica "Liquidar y cobrar los cargos del cierre" (SB-14).</summary>
public sealed record CargosDelCierreCobrados(
    string NumeroDelArriendo,
    DateTime HoraDeRegreso,
    decimal ValorDelCombustible,
    decimal ValorDelTiempoAdicional
) : IEvento
{
    /// <summary>Nombre del evento en el modelo.</summary>
    public string NombreEnElModelo => "Cargos del cierre cobrados";

    /// <summary>Identidad de la raíz.</summary>
    public string Identidad => NumeroDelArriendo;
}
