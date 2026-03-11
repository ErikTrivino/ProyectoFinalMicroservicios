using Microsoft.EntityFrameworkCore;
using NotificacionesService.Data;
using NotificacionesService.Services;

var builder = WebApplication.CreateBuilder(args);

// =========================
// Configuración de servicios
// =========================

// Controllers
builder.Services.AddControllers();

// PostgreSQL con Entity Framework
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
builder.Services.AddDbContext<NotificacionesDbContext>(options =>
    options.UseNpgsql(connectionString));

// Swagger/OpenAPI
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new Microsoft.OpenApi.Models.OpenApiInfo
    {
        Title = "API Notificaciones",
        Version = "v1",
        Description = "Servicio de gestión de notificaciones - Reto 3 Microservicios"
    });
});

// RabbitMQ Consumer (BackgroundService)
builder.Services.AddHostedService<RabbitMQConsumerService>();

var app = builder.Build();

// =========================
// Inicialización de BD
// =========================
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<NotificacionesDbContext>();
    
    // Reintentar conexión a la BD (esperar a que PostgreSQL esté listo)
    var maxRetries = 10;
    for (int i = 0; i < maxRetries; i++)
    {
        try
        {
            db.Database.EnsureCreated();
            Console.WriteLine("[DB] Base de datos inicializada correctamente.");
            break;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[DB] Intento {i + 1}/{maxRetries} - Error: {ex.Message}");
            Thread.Sleep(3000);
        }
    }
}

// =========================
// Pipeline HTTP
// =========================

// Swagger UI disponible siempre (no solo en Development)
app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "API Notificaciones v1");
    c.RoutePrefix = "swagger";
});

app.MapControllers();

Console.WriteLine("[APP] Servicio de Notificaciones iniciado en puerto 8084");
app.Run();
