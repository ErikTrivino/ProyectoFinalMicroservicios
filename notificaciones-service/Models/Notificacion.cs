using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace NotificacionesService.Models;

[Table("notificaciones")]
public class Notificacion
{
    [Key]
    [Column("id")]
    public string Id { get; set; } = Guid.NewGuid().ToString();

    [Required]
    [Column("tipo")]
    [MaxLength(50)]
    public string Tipo { get; set; } = string.Empty; // BIENVENIDA | DESVINCULACION

    [Required]
    [Column("destinatario")]
    [MaxLength(100)]
    public string Destinatario { get; set; } = string.Empty; // email

    [Required]
    [Column("mensaje")]
    public string Mensaje { get; set; } = string.Empty;

    [Required]
    [Column("fecha_envio")]
    public DateTime FechaEnvio { get; set; } = DateTime.UtcNow;

    [Required]
    [Column("empleado_id")]
    [MaxLength(36)]
    public string EmpleadoId { get; set; } = string.Empty;
}
