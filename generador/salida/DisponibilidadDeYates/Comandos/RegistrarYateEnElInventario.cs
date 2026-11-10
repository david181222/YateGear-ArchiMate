// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Registrar yate en el inventario" (SB-01, id-8e392207203f40b2b0a50bcbe62efc90).
namespace YateGear.DisponibilidadDeYates;

public sealed partial class RegistrarYateEnElInventarioManejador
{
    // Reglas del "Contrato de servicio: Registrar yate en el inventario" (id-431ca877f2e34dd2b6243038d1bb256f):
    //   Se rechaza si el propietario no tiene contrato firmado (INT-CON) o si los documentos del yate ante
    //   la DIMAR no están al día (NOR-01).
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("REG-01", "motivo");
    partial void ValidarReglas(RegistrarYateEnElInventarioDatos datos)
    {
        // INT-CON y NOR-01: declaradas en el YAML (reglas); la revisa el código generado antes de llamar aquí.
    }
}
