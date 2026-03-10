using System.Text.Json.Serialization;

namespace NotificacionesService.DTOs;

/// <summary>
/// DTO que representa el evento empleado.eliminado publicado por empleados-service
/// </summary>
public class EmpleadoEliminadoEvent
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("nombre")]
    public string Nombre { get; set; } = string.Empty;

    [JsonPropertyName("email")]
    public string Email { get; set; } = string.Empty;
}
