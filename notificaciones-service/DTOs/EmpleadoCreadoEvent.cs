using System.Text.Json.Serialization;

namespace NotificacionesService.DTOs;

/// <summary>
/// DTO que representa el evento empleado.creado publicado por empleados-service
/// </summary>
public class EmpleadoCreadoEvent
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("nombre")]
    public string Nombre { get; set; } = string.Empty;

    [JsonPropertyName("email")]
    public string Email { get; set; } = string.Empty;

    [JsonPropertyName("departamentoId")]
    public string DepartamentoId { get; set; } = string.Empty;

    [JsonPropertyName("fechaIngreso")]
    public string FechaIngreso { get; set; } = string.Empty;
}
