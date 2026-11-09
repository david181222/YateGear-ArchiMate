// Generado desde ArchiMate: ApplicationService "Catálogo de la biblioteca" (SA-01, id-ae10d4fa9958587aa03b1c8536870bb3).
// No editar: el generador reescribe este archivo.
#nullable enable
namespace Biblioteca.Prestamos;

/// <summary>Entrada del servicio SA "Catálogo de la biblioteca" (SA-01).</summary>
public sealed record CatalogoDeLaBibliotecaEntrada(
    string Libro
);

/// <summary>Salida del servicio SA "Catálogo de la biblioteca" (SA-01).</summary>
public sealed record CatalogoDeLaBibliotecaSalida(
    bool Disponible
);

/// <summary>Servicio de la capa anticorrupción "Catálogo de la biblioteca" (SA-01).</summary>
/// <remarks>
/// <para>Interfaz: "Interfaz del catálogo" (id-bd12ff4c48e651eb91ff722ffd2d41fe).
/// Contraparte: ApplicationComponent "Sistema del catálogo" (id-f96fb87fb5e759699af89f8e28598a96), sistema externo.</para>
/// <para>Flujos: sale "Consulta del libro" (id-82e9dfaeb1e95ee8bca50ff5107b6c70); entra "Estado del libro" (id-bb752d7b8aa0564a9d2ea5cd62208367).</para>
/// <para>Contrato de servicio: Catálogo de la biblioteca (id-5ee7ad76766c50d7abc0cfeea3d26980). Entrada: El libro.
/// Salida: Si el libro está disponible. Reglas: La aplicación no cambia el catálogo; solo lo consulta.</para>
/// </remarks>
public interface ICatalogoDeLaBiblioteca
{
    /// <summary>Llama al servicio.</summary>
    CatalogoDeLaBibliotecaSalida Llamar(CatalogoDeLaBibliotecaEntrada entrada);
}

/// <summary>"Sistema del catálogo" simulado: responde con los valores fijos del YAML
/// (casos en orden y, si ninguno se cumple, respuesta_por_defecto).</summary>
public sealed class CatalogoDeLaBibliotecaSimulado(Bitacora bitacora) : ICatalogoDeLaBiblioteca
{
    /// <inheritdoc />
    public CatalogoDeLaBibliotecaSalida Llamar(CatalogoDeLaBibliotecaEntrada entrada)
    {
        var respuesta =
            (entrada.Libro == "LIBRO-PRESTADO") ? new CatalogoDeLaBibliotecaSalida(false) :
            new CatalogoDeLaBibliotecaSalida(true);
        bitacora.Anotar("llamada a servicio SA", "Catálogo de la biblioteca", new { entrada, respuesta });
        return respuesta;
    }
}
