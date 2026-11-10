// Generado desde ArchiMate: Model "Biblioteca" (id-2978acbbf99b509f9ea9ee63176d70ae).
// Programa (host): levanta los contextos generados en un solo proceso, con el bus entre contextos (D1).
// No editar: el generador reescribe este archivo. El puerto (5080) se elige al generar
// (generar.ps1 -Puerto); para una sola vez: ejecutar.ps1 -Puerto.
#nullable enable
using Biblioteca.Integracion;

var builder = WebApplication.CreateBuilder(args);
builder.Services.ConfigureHttpJsonOptions(o => Json.Configurar(o.SerializerOptions));
builder.Services.AddSingleton<BusEntreContextos>();

// Contextos.
Biblioteca.Prestamos.Registro.AgregarServicios(builder.Services);         // Contexto Préstamos

var app = builder.Build();
// Página de inicio (infraestructura, no sale del modelo): wwwroot/index.html, con las rutas de cada contexto.
app.UseDefaultFiles();
app.UseStaticFiles();
Biblioteca.Prestamos.Registro.MapearEndpoints(app);

// Infraestructura (no sale del modelo): los contextos generados y los eventos que pasaron por el bus entre contextos.
app.MapGet("/contextos", () => new[]
{
    new { nombre = "Contexto Préstamos", ruta = "/prestamos" },
});
app.MapGet("/eventos-entre-contextos", (BusEntreContextos bus) => bus.Historial());
// La ruta de cada contexto lleva a su parte de la página de inicio.
app.MapGet("/prestamos", () => Results.Redirect("/#prestamos"));

app.Run();
