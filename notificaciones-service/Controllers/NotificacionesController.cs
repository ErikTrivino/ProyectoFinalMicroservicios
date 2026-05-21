using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using NotificacionesService.Data;
using NotificacionesService.DTOs;
using NotificacionesService.Models;


namespace NotificacionesService.Controllers;

[ApiController]
[Route("[controller]")]
[Produces("application/json")]
[Authorize(Roles = "USER,ADMIN")]
public class NotificacionesController : ControllerBase
{
    private readonly NotificacionesDbContext _context;
    private readonly ILogger<NotificacionesController> _logger;

    public NotificacionesController(
        NotificacionesDbContext context,
        ILogger<NotificacionesController> logger)
    {
        _context = context;
        _logger = logger;
    }

    /// <summary>
    /// Lista todas las notificaciones registradas
    /// </summary>
    /// <returns>Lista de notificaciones</returns>
    [HttpGet]
    [ProducesResponseType(typeof(ApiResponse<List<Notificacion>>), StatusCodes.Status200OK)]
    public async Task<IActionResult> ListarNotificaciones()
    {
        _logger.LogInformation("[API] GET /notificaciones");

        var notificaciones = await _context.Notificaciones
            .OrderByDescending(n => n.FechaEnvio)
            .ToListAsync();

        return Ok(ApiResponse<List<Notificacion>>.Ok(
            "Lista de notificaciones",
            notificaciones));
    }

    /// <summary>
    /// Lista las notificaciones de un empleado específico
    /// </summary>
    /// <param name="empleadoId">ID del empleado</param>
    /// <returns>Lista de notificaciones del empleado</returns>
    [HttpGet("{empleadoId}")]
    [ProducesResponseType(typeof(ApiResponse<List<Notificacion>>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object>), StatusCodes.Status404NotFound)]
    public async Task<IActionResult> ObtenerNotificacionesPorEmpleado(string empleadoId)
    {
        _logger.LogInformation("[API] GET /notificaciones/{EmpleadoId}", empleadoId);

        var notificaciones = await _context.Notificaciones
            .Where(n => n.EmpleadoId == empleadoId)
            .OrderByDescending(n => n.FechaEnvio)
            .ToListAsync();

        if (notificaciones.Count == 0)
        {
            return NotFound(ApiResponse<object>.Error(
                $"No se encontraron notificaciones para el empleado: {empleadoId}"));
        }

        return Ok(ApiResponse<List<Notificacion>>.Ok(
            $"Notificaciones del empleado {empleadoId}",
            notificaciones));
    }
}
