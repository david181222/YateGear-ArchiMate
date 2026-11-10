// Generado desde ArchiMate: Model "YateGear" (id-98e02fd4df1c4f21a8610d291649a7af).
// Programa (host): levanta los contextos generados en un solo proceso, con el bus entre contextos (D1).
// No editar: el generador reescribe este archivo. El puerto (5080) se elige al generar
// (generar.ps1 -Puerto); para una sola vez: ejecutar.ps1 -Puerto.
#nullable enable
using System.Text.Json;
using Microsoft.AspNetCore.Http.Metadata;
using Microsoft.AspNetCore.OpenApi;
using YateGear.Integracion;

var builder = WebApplication.CreateBuilder(args);
builder.Services.ConfigureHttpJsonOptions(o => Json.Configurar(o.SerializerOptions));
builder.Services.AddSingleton<BusEntreContextos>();
// Documentación de la API (infraestructura, no sale del modelo): el documento OpenAPI con todos los endpoints.
builder.Services.AddOpenApi(o =>
{
    // El nombre de cada esquema lleva su contexto, porque cada contexto tiene sus propias clases y algunas se
    // llaman igual (por ejemplo, un evento que un contexto publica y otro recibe).
    o.CreateSchemaReferenceId = tipo =>
    {
        var id = OpenApiOptions.CreateDefaultSchemaReferenceId(tipo);
        return id is null || tipo.Type.Namespace is null ? id : $"{tipo.Type.Namespace.Split('.').Last()}.{id}";
    };
    // Un evento de otro contexto y un mensaje de un servicio SA se reciben como JSON, para decir qué dato obligatorio
    // falta; en el documento se muestran con la forma de su record, la que su endpoint declara con Accepts.
    o.AddOperationTransformer(async (operacion, contexto, cancelacion) =>
    {
        var declarado = contexto.Description.ActionDescriptor.EndpointMetadata.OfType<IAcceptsMetadata>().LastOrDefault()?.RequestType;
        var recibeJson = contexto.Description.ParameterDescriptions.Any(p => p.Type == typeof(JsonElement));
        if (recibeJson && declarado is not null && declarado != typeof(JsonElement)
            && operacion.RequestBody?.Content?.TryGetValue("application/json", out var cuerpo) == true)
        {
            cuerpo.Schema = await contexto.GetOrCreateSchemaAsync(declarado, null, cancelacion);
        }
    });
    o.AddDocumentTransformer((documento, _, _) =>
    {
        documento.Info.Title = "YateGear";
        documento.Info.Description = "API generada desde el modelo ArchiMate \"YateGear\": 5 contexto(s) en un solo programa. Cada endpoint dice de qué elemento del modelo sale y su contrato.";
        return Task.CompletedTask;
    });
});

// Contextos.
YateGear.Calificaciones.Registro.AgregarServicios(builder.Services);         // Contexto Calificaciones
YateGear.CobrosYDeposito.Registro.AgregarServicios(builder.Services);         // Contexto Cobros y depósito
YateGear.DisponibilidadDeYates.Registro.AgregarServicios(builder.Services);         // Contexto Disponibilidad de yates
YateGear.GestionDelArriendo.Registro.AgregarServicios(builder.Services);         // Contexto Gestión del arriendo
YateGear.OperacionDelArriendo.Registro.AgregarServicios(builder.Services);         // Contexto Operación del arriendo

var app = builder.Build();
// Página de inicio (infraestructura, no sale del modelo): wwwroot/index.html, con las rutas de cada contexto.
app.UseDefaultFiles();
app.UseStaticFiles();
// Documentación de la API: el documento en /openapi/v1.json y la página para probarla en /swagger.
app.MapOpenApi();
app.UseSwaggerUI(o => o.SwaggerEndpoint("/openapi/v1.json", "YateGear"));
YateGear.Calificaciones.Registro.MapearEndpoints(app);
YateGear.CobrosYDeposito.Registro.MapearEndpoints(app);
YateGear.DisponibilidadDeYates.Registro.MapearEndpoints(app);
YateGear.GestionDelArriendo.Registro.MapearEndpoints(app);
YateGear.OperacionDelArriendo.Registro.MapearEndpoints(app);

// Infraestructura (no sale del modelo): los contextos generados y los eventos que pasaron por el bus entre contextos.
app.MapGet("/contextos", () => new[]
{
    new { nombre = "Contexto Calificaciones", ruta = "/calificaciones" },
    new { nombre = "Contexto Cobros y depósito", ruta = "/cobros-y-deposito" },
    new { nombre = "Contexto Disponibilidad de yates", ruta = "/disponibilidad-de-yates" },
    new { nombre = "Contexto Gestión del arriendo", ruta = "/gestion-del-arriendo" },
    new { nombre = "Contexto Operación del arriendo", ruta = "/operacion-del-arriendo" },
}).WithTags("Infraestructura").WithSummary("Los contextos que levantó el programa");
app.MapGet("/eventos-entre-contextos", (BusEntreContextos bus) => bus.Historial())
    .WithTags("Infraestructura").WithSummary("Los eventos que pasaron por el bus entre contextos y los errores de sus suscriptores");
// La ruta de cada contexto lleva a su parte de la página de inicio.
app.MapGet("/calificaciones", () => Results.Redirect("/#calificaciones")).ExcludeFromDescription();
app.MapGet("/cobros-y-deposito", () => Results.Redirect("/#cobros-y-deposito")).ExcludeFromDescription();
app.MapGet("/disponibilidad-de-yates", () => Results.Redirect("/#disponibilidad-de-yates")).ExcludeFromDescription();
app.MapGet("/gestion-del-arriendo", () => Results.Redirect("/#gestion-del-arriendo")).ExcludeFromDescription();
app.MapGet("/operacion-del-arriendo", () => Results.Redirect("/#operacion-del-arriendo")).ExcludeFromDescription();

app.Run();
