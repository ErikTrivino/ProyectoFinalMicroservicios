using System.Text.Json.Serialization;

namespace NotificacionesService.DTOs;

public class UsuarioEvent
{
    [JsonPropertyName("email")]
    public string Email { get; set; } = string.Empty;

    [JsonPropertyName("token")]
    public string? Token { get; set; }

    [JsonPropertyName("tipo")]
    public string Tipo { get; set; } = string.Empty;

    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("empleadoId")]
    public string? EmpleadoId { get; set; }

    [JsonPropertyName("needsPasswordReset")]
    public bool? NeedsPasswordReset { get; set; }

    [JsonPropertyName("hasInitialPassword")]
    public bool? HasInitialPassword { get; set; }
}
