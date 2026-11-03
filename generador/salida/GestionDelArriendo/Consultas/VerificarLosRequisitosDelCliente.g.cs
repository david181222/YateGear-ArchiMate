// Generado desde ArchiMate: ApplicationService "Verificar los requisitos del cliente" (SB-11, id-8de1e624fe6d42b58cae281366f1e86a).
// No editar: el generador reescribe este archivo. Las reglas y los datos calculados van en VerificarLosRequisitosDelCliente.cs.
#nullable enable
namespace YateGear.GestionDelArriendo;

/// <summary>Entrada de la consulta "Verificar los requisitos del cliente" (SB-11).</summary>
public sealed record VerificarLosRequisitosDelCliente(
    string NumeroDelArriendo
);

/// <summary>Salida de la consulta "Verificar los requisitos del cliente".</summary>
public sealed record VerificarLosRequisitosDelClienteSalida(
    bool Cumple,
    string? Motivo
);

/// <summary>Lo que reciben ValidarReglas y los datos calculados: la consulta y la raíz.</summary>
public sealed record VerificarLosRequisitosDelClienteDatos(VerificarLosRequisitosDelCliente Consulta, Arriendo Arriendo);

/// <summary>Manejador de la consulta "Verificar los requisitos del cliente" (SB-11). No cambia la raíz.</summary>
/// <remarks>
/// <para>Contrato de servicio: Verificar los requisitos del cliente (id-8dfaf8632e6042d3a86c8dcc1dbf95df), asociado al servicio de negocio
/// "Verificar los requisitos del cliente" (id-2d99dc8136174976b9d7f68a2ed30efe).</para>
/// <para>Entrada: Cliente, número y vigencia de la licencia de navegación y autorización de datos (fecha y terceros autorizados: evaluadora, aseguradora y pasarela).</para>
/// <para>Salida: Cumple o no cumple, con el motivo.</para>
/// <para>Reglas: Se rechaza sin licencia de navegación vigente (H-09, NOR-01) o sin autorización del cliente para compartir sus datos con terceros (Ley 1581, H-19). Van como comentario en ValidarReglas.</para>
/// </remarks>
public sealed partial class VerificarLosRequisitosDelClienteManejador(Repositorio<Arriendo> repositorio)
{
    /// <summary>Reglas del contrato. Se escribe en el archivo manual.</summary>
    partial void ValidarReglas(VerificarLosRequisitosDelClienteDatos datos);

    /// <summary>Dato calculado "cumple". Se escribe en el archivo manual.</summary>
    private partial bool Cumple(VerificarLosRequisitosDelClienteDatos datos);

    /// <summary>Dato calculado "motivo". Se escribe en el archivo manual.</summary>
    private partial string? Motivo(VerificarLosRequisitosDelClienteDatos datos);

    /// <summary>Ejecuta la consulta.</summary>
    public VerificarLosRequisitosDelClienteSalida Manejar(VerificarLosRequisitosDelCliente consulta)
    {
        var arriendo = repositorio.Obtener(consulta.NumeroDelArriendo)
            ?? throw new NoEncontrado($"No existe arriendo {consulta.NumeroDelArriendo}.");
        var datos = new VerificarLosRequisitosDelClienteDatos(consulta, arriendo);
        ValidarReglas(datos);
        return new VerificarLosRequisitosDelClienteSalida(
            Cumple(datos),
            Motivo(datos)
        );
    }
}
