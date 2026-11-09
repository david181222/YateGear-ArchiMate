// Generado desde ArchiMate: Model "YateGear" (id-98e02fd4df1c4f21a8610d291649a7af).
// Programa (host): levanta los contextos generados en un solo proceso, con el bus entre contextos (D1).
// No editar: el generador reescribe este archivo. El puerto (5080) sale de PUERTO en src/generar.py;
// para una sola vez: ejecutar.ps1 -Puerto.
#nullable enable
using YateGear.Integracion;

var builder = WebApplication.CreateBuilder(args);
builder.Services.ConfigureHttpJsonOptions(o => Json.Configurar(o.SerializerOptions));
builder.Services.AddSingleton<BusEntreContextos>();

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
});
app.MapGet("/eventos-entre-contextos", (BusEntreContextos bus) => bus.Historial());
// La ruta de cada contexto lleva a su parte de la página de inicio.
app.MapGet("/calificaciones", () => Results.Redirect("/#calificaciones"));
app.MapGet("/cobros-y-deposito", () => Results.Redirect("/#cobros-y-deposito"));
app.MapGet("/disponibilidad-de-yates", () => Results.Redirect("/#disponibilidad-de-yates"));
app.MapGet("/gestion-del-arriendo", () => Results.Redirect("/#gestion-del-arriendo"));
app.MapGet("/operacion-del-arriendo", () => Results.Redirect("/#operacion-del-arriendo"));

app.Run();
