// Generado desde ArchiMate: ApplicationService "Ubicación y combustible del proveedor" (SA-07, id-ec3bc54925a940ccbbcb5ac42ee8479c).
// Capa anticorrupción, lo que entra (G7): lo que el sistema externo le envía a YateGear por este servicio SA
// (recibe del YAML). No editar: el generador reescribe este archivo.
#nullable enable
using System.Text.Json;

namespace YateGear.OperacionDelArriendo;

/// <summary>Mensaje "Lectura del proveedor" que "Ubicación y combustible del proveedor" recibe del sistema externo. Dispara "Registrar lecturas de ubicación y combustible".</summary>
public sealed record LecturaDelProveedor(
    string IdentificadorDelYate,
    decimal Latitud,
    decimal Longitud,
    decimal NivelDeCombustible,
    DateTime HoraDeLaLectura
);

/// <summary>Recibe lo que "Plataforma del proveedor de ubicación y combustible" le envía a YateGear por "Ubicación y combustible del proveedor" (SA-07)
/// y dispara el comando de cada mensaje, con sus datos por nombre.</summary>
/// <remarks>
/// <para>Contrato de servicio: Ubicación y combustible del proveedor (id-a380456bbb084bc7b84ac707207538a9). Entrada: Lectura del proveedor.</para>
/// <para>Interfaz "Interfaz con el proveedor de ubicación y combustible" (id-02a9010b307c4368b958c8cdb9884ca1).</para>
/// </remarks>
public sealed class ReceptorDeUbicacionYCombustibleDelProveedor(
    Bitacora bitacora,
    RegistrarLecturasDeUbicacionYCombustibleManejador registrarLecturasDeUbicacionYCombustible
)
{
    /// <summary>Lee "Lectura del proveedor" desde JSON (si falta un dato obligatorio, DatoFaltante: 422) y dispara "Registrar lecturas de ubicación y combustible".</summary>
    public RespuestaDeComando RecibirLecturaDelProveedor(JsonElement json)
    {
        var mensaje = LectorDeEventos.Leer<LecturaDelProveedor>(json, ("identificadorDelYate", "identificador del yate"), ("latitud", "latitud"), ("longitud", "longitud"), ("nivelDeCombustible", "nivel de combustible"), ("horaDeLaLectura", "hora de la lectura"));
        bitacora.Anotar("mensaje recibido", "Ubicación y combustible del proveedor: Lectura del proveedor", mensaje);
        return registrarLecturasDeUbicacionYCombustible.Manejar(new RegistrarLecturasDeUbicacionYCombustible(mensaje.IdentificadorDelYate, mensaje.Latitud, mensaje.Longitud, mensaje.NivelDeCombustible, mensaje.HoraDeLaLectura));
    }
}
