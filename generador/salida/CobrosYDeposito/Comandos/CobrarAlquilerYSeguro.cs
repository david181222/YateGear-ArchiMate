// Archivo manual: el generador lo creó una sola vez y nunca lo sobrescribe.
// Generado desde ArchiMate: ApplicationProcess "Cobrar alquiler y seguro" (SB-13, id-e5737d28667c4b8a9373ac6f62271f96).
namespace YateGear.CobrosYDeposito;

public sealed partial class CobrarAlquilerYSeguroManejador
{
    // Reglas del "Contrato de servicio: Cobrar alquiler y seguro" (id-0630fc686f76430196499d225b64d38a):
    //   El contrato no tiene reglas.
    //
    // Se llama antes de la transición de estado. Para rechazar la operación:
    //   throw new ReglaIncumplida("<código de la regla>", "motivo");
    partial void ValidarReglas(CobrarAlquilerYSeguroDatos datos)
    {
        // INT-PAG (invariante de la V6.2), escrita a mano: un cobro sin confirmación de la pasarela no cuenta como pagado.
        if (!datos.CobrosPorLaPasarelaDePagos1.Aprobada || !datos.CobrosPorLaPasarelaDePagos2.Aprobada)
        {
            throw new ReglaIncumplida("INT-PAG", "La pasarela no aprobó el cobro del alquiler o el del seguro.");
        }
    }

    // Escrito a mano: el alquiler es el precio por día por los días del arriendo (entrada de SB-13).
    private partial decimal ValorDelAlquiler(int dias, decimal precioPorDia) => dias * precioPorDia;
}
