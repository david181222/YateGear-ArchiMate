// Generado desde ArchiMate: DataObject "Calendario del yate" (id-b3dcca7f045e43f49523fe907a138a79).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace YateGear.DisponibilidadDeYates;

/// <summary>Raíz "Calendario del yate" del "Agregado Calendario del yate" (id-85399b46487d42d0b1f00ed00e7a0890).</summary>
public sealed partial class CalendarioDelYate : IRaiz
{
    /// <summary>Identidad: identificador del yate. Se forma con identificador del yate, separados con "/".</summary>
    public string IdentificadorDelYate { get; private set; } = "";

    /// <summary>Estado de la raíz (lista cerrada del YAML).</summary>
    public EstadoDelCalendario Estado { get; set; }

    /// <summary>Objeto de valor "Rango de fechas", Cardinalidad Muchos (composición id-31b5283dd5954622aeedaddc51af4662).</summary>
    public List<RangoDeFechas> RangoDeFechas { get; set; } = [];

    string IRaiz.Identidad => IdentificadorDelYate;

    void IRaiz.AsignarIdentidad(string identidad) => IdentificadorDelYate = identidad;
}
