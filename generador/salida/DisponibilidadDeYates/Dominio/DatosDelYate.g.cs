// Generado desde ArchiMate: DataObject "Datos del yate" (id-0d2603fc1ad64e65a7eca9f214792093).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Objeto de valor "Datos del yate" de la raíz "Yate", Cardinalidad Uno.
/// Campos: nombre (string); matrícula (string); capacidad (int).</summary>
public sealed record DatosDelYate(
    string Nombre,
    string Matricula,
    int Capacidad
);
