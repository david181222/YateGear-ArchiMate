// Generado desde ArchiMate: DataObject "Rango de fechas" (id-ada4b300178d4ff6a7a01bc9405f74fb).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Objeto de valor "Rango de fechas" de la raíz "Calendario del yate", Cardinalidad Muchos.
/// Campos: inicio (DateOnly); fin (DateOnly); estado de la fecha (enum Estado de la fecha(bloqueada, apartada, ocupada)); número del arriendo (string?).</summary>
public sealed record RangoDeFechas(
    DateOnly Inicio,
    DateOnly Fin,
    EstadoDeLaFecha EstadoDeLaFecha,
    string? NumeroDelArriendo
);
