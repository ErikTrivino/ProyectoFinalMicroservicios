using System.Text;
using System.Text.Json;
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using NotificacionesService.Data;
using NotificacionesService.DTOs;
using NotificacionesService.Models;
using System.Diagnostics;

namespace NotificacionesService.Services;

/// <summary>
/// Servicio en background que consume eventos de RabbitMQ
/// Escucha los eventos de empleados y usuarios (Seguridad)
/// </summary>
public class RabbitMQConsumerService : BackgroundService
{
    private static readonly ActivitySource ActivitySource = new("NotificacionesService");
    private readonly ILogger<RabbitMQConsumerService> _logger;
    private readonly IServiceProvider _serviceProvider;
    private readonly IConfiguration _configuration;
    
    private IConnection? _connection;
    private IChannel? _channel;

    // Exchanges (deben coincidir con los de Python)
    private const string EXCHANGE_EMPLEADOS = "empleados_events";
    private const string EXCHANGE_USUARIOS = "usuario_events";

    // Colas exclusivas de este servicio
    private const string QUEUE_NOTIFICACIONES = "notificaciones.general.queue";

    public RabbitMQConsumerService(
        ILogger<RabbitMQConsumerService> logger,
        IServiceProvider serviceProvider,
        IConfiguration configuration)
    {
        _logger = logger;
        _serviceProvider = serviceProvider;
        _configuration = configuration;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("[RABBITMQ] Iniciando consumidor de eventos (V2 - Actualizado)...");

        // Esperar a que RabbitMQ esté disponible
        await WaitForRabbitMQ(stoppingToken);

        await InitializeRabbitMQ();

        // Mantener el servicio corriendo
        while (!stoppingToken.IsCancellationRequested)
        {
            await Task.Delay(1000, stoppingToken);
        }
    }

    private async Task WaitForRabbitMQ(CancellationToken stoppingToken)
    {
        var host = _configuration["RabbitMQ:Host"] ?? "localhost";
        var port = int.Parse(_configuration["RabbitMQ:Port"] ?? "5672");
        var user = _configuration["RabbitMQ:User"] ?? "admin";
        var password = _configuration["RabbitMQ:Password"] ?? "admin";

        var factory = new ConnectionFactory
        {
            HostName = host,
            Port = port,
            UserName = user,
            Password = password
        };

        var maxRetries = 15;
        var retryCount = 0;

        while (retryCount < maxRetries && !stoppingToken.IsCancellationRequested)
        {
            try
            {
                _connection = await factory.CreateConnectionAsync(stoppingToken);
                _logger.LogInformation("[RABBITMQ] Conexión establecida con {Host}:{Port}", host, port);
                return;
            }
            catch (Exception ex)
            {
                retryCount++;
                _logger.LogWarning("[RABBITMQ] Intento {Retry}/{Max} - Error conectando: {Error}", 
                    retryCount, maxRetries, ex.Message);
                await Task.Delay(3000, stoppingToken);
            }
        }

        throw new Exception("No se pudo conectar a RabbitMQ después de varios intentos");
    }

    private async Task InitializeRabbitMQ()
    {
        if (_connection == null) return;

        _channel = await _connection.CreateChannelAsync();

        // Declarar exchanges tipo fanout (deben coincidir con Python)
        await _channel.ExchangeDeclareAsync(EXCHANGE_EMPLEADOS, ExchangeType.Fanout, durable: true);
        await _channel.ExchangeDeclareAsync(EXCHANGE_USUARIOS, ExchangeType.Fanout, durable: true);

        // Declarar cola general para este servicio
        await _channel.QueueDeclareAsync(QUEUE_NOTIFICACIONES, durable: true, exclusive: false, autoDelete: false);

        // Binding: conectar cola a ambos exchanges
        await _channel.QueueBindAsync(QUEUE_NOTIFICACIONES, EXCHANGE_EMPLEADOS, string.Empty);
        await _channel.QueueBindAsync(QUEUE_NOTIFICACIONES, EXCHANGE_USUARIOS, string.Empty);

        // Configurar consumidor único
        var consumer = new AsyncEventingBasicConsumer(_channel);
        consumer.ReceivedAsync += OnMessageReceived;
        
        await _channel.BasicConsumeAsync(QUEUE_NOTIFICACIONES, autoAck: false, consumer: consumer);

        _logger.LogInformation("[RABBITMQ] Consumidor configurado para {Ex1} y {Ex2}. Escuchando...", EXCHANGE_EMPLEADOS, EXCHANGE_USUARIOS);
    }

    private async Task OnMessageReceived(object sender, BasicDeliverEventArgs ea)
    {
        try
        {
            var body = ea.Body.ToArray();
            var json = Encoding.UTF8.GetString(body);
            
            // Intentar detectar el tipo de evento
            var baseEvent = JsonSerializer.Deserialize<JsonElement>(json);
            string? eventType = null;
            
            if (baseEvent.TryGetProperty("tipo", out var tipoProp))
            {
                eventType = tipoProp.GetString();
            }
            else if (!string.IsNullOrEmpty(ea.BasicProperties.Type))
            {
                eventType = ea.BasicProperties.Type;
            }

            _logger.LogInformation("[EVENTO] Recibido {Type}: {Json}", eventType ?? "DESCONOCIDO", json);

            using var activity = StartConsumerActivity(ea, eventType);

            switch (eventType)
            {
                case "empleado.creado":
                    await ProcesarEmpleadoCreado(json);
                    break;
                case "empleado.eliminado":
                    await ProcesarEmpleadoEliminado(json);
                    break;
                case "usuario.creado":
                case "usuario.recuperacion":
                    await ProcesarUsuarioSeguridad(json);
                    break;
                case "vacaciones.programadas":
                    await ProcesarVacacionesProgramadas(json);
                    break;
                case "empleado.estado.cambiado":
                    await ProcesarEmpleadoEstadoCambiado(json);
                    break;
                default:
                    _logger.LogWarning("[EVENTO] Tipo de evento no soportado: {Type}", eventType);
                    break;
            }

            await _channel!.BasicAckAsync(ea.DeliveryTag, false);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[EVENTO] Error procesando mensaje");
            // Nack con requeue true para reintentar si es error transitorio
            await _channel!.BasicNackAsync(ea.DeliveryTag, false, true);
        }
    }

    private async Task ProcesarVacacionesProgramadas(string json)
    {
        var evento = JsonSerializer.Deserialize<JsonElement>(json);
        var email = evento.TryGetProperty("email", out var emailProp) ? emailProp.GetString() : null;
        var empleadoId = evento.TryGetProperty("empleado_id", out var idProp) ? idProp.GetString() : "SISTEMA";
        var fechaInicio = evento.TryGetProperty("fecha_inicio", out var fiProp) ? fiProp.GetString() : "";
        var fechaFin = evento.TryGetProperty("fecha_fin", out var ffProp) ? ffProp.GetString() : "";

        if (string.IsNullOrEmpty(email))
        {
            _logger.LogWarning("[NOTIFICACION] Evento vacaciones.programadas ignorado por falta de email.");
            return;
        }

        var notificacion = new Notificacion
        {
            Id = Guid.NewGuid().ToString(),
            Tipo = "VACACIONES",
            Destinatario = email,
            Mensaje = $"Tus vacaciones han sido programadas exitosamente. Período: {fechaInicio} al {fechaFin}.",
            FechaEnvio = DateTime.UtcNow,
            EmpleadoId = empleadoId
        };

        await GuardarNotificacion(notificacion);
        _logger.LogInformation("[NOTIFICACION] Vacaciones programadas procesadas y guardadas para {Email}", email);
    }

    private async Task ProcesarEmpleadoEstadoCambiado(string json)
    {
        var evento = JsonSerializer.Deserialize<JsonElement>(json);
        var email = evento.TryGetProperty("email", out var emailProp) ? emailProp.GetString() : null;
        var empleadoId = evento.TryGetProperty("empleado_id", out var idProp) ? idProp.GetString() : "SISTEMA";
        var nuevoEstado = evento.TryGetProperty("nuevoEstado", out var neProp) ? neProp.GetString() : "";
        var motivo = evento.TryGetProperty("motivo", out var mProp) ? mProp.GetString() : "";

        if (string.IsNullOrEmpty(email))
        {
            _logger.LogWarning("[NOTIFICACION] Evento empleado.estado.cambiado ignorado por falta de email.");
            return;
        }

        string mensaje = nuevoEstado switch
        {
            "EN_VACACIONES" => "Tus vacaciones han comenzado y tus credenciales han sido desactivadas temporalmente. ¡Que disfrutes tu descanso!",
            "ACTIVO" => "Tus vacaciones han finalizado y tus credenciales han sido reactivadas. ¡Bienvenido de vuelta!",
            _ => $"Tu estado ha cambiado a {nuevoEstado}. Motivo: {motivo}"
        };

        var notificacion = new Notificacion
        {
            Id = Guid.NewGuid().ToString(),
            Tipo = "ESTADO_CAMBIADO",
            Destinatario = email,
            Mensaje = mensaje,
            FechaEnvio = DateTime.UtcNow,
            EmpleadoId = empleadoId
        };

        await GuardarNotificacion(notificacion);
        _logger.LogInformation("[NOTIFICACION] Cambio de estado de empleado procesado y guardado para {Email}", email);
    }

    private static Activity? StartConsumerActivity(BasicDeliverEventArgs ea, string? eventType)
    {
        var parentContext = ExtractParentContext(ea);
        var activityName = $"rabbitmq consume {eventType ?? "desconocido"}";
        return parentContext == default
            ? ActivitySource.StartActivity(activityName, ActivityKind.Consumer)
            : ActivitySource.StartActivity(activityName, ActivityKind.Consumer, parentContext);
    }

    private static ActivityContext ExtractParentContext(BasicDeliverEventArgs ea)
    {
        var headers = ea.BasicProperties.Headers;
        if (headers == null || !headers.TryGetValue("traceparent", out var traceparentValue))
        {
            return default;
        }

        var traceparent = HeaderToString(traceparentValue);
        if (string.IsNullOrWhiteSpace(traceparent))
        {
            return default;
        }

        var tracestate = headers.TryGetValue("tracestate", out var tracestateValue)
            ? HeaderToString(tracestateValue)
            : null;

        return ActivityContext.TryParse(traceparent, tracestate, out var context)
            ? context
            : default;
    }

    private static string? HeaderToString(object? value)
    {
        return value switch
        {
            null => null,
            byte[] bytes => Encoding.UTF8.GetString(bytes),
            ReadOnlyMemory<byte> bytes => Encoding.UTF8.GetString(bytes.Span),
            string text => text,
            _ => value.ToString()
        };
    }

    private async Task ProcesarEmpleadoCreado(string json)
    {
        var evento = JsonSerializer.Deserialize<EmpleadoCreadoEvent>(json);
        if (evento == null) return;

        var notificacion = new Notificacion
        {
            Id = Guid.NewGuid().ToString(),
            Tipo = "BIENVENIDA",
            Destinatario = evento.Email,
            Mensaje = $"Bienvenido {evento.Nombre} a la empresa. Tu cuenta está siendo procesada.",
            FechaEnvio = DateTime.UtcNow,
            EmpleadoId = evento.Id
        };

        await GuardarNotificacion(notificacion);
    }

    private async Task ProcesarEmpleadoEliminado(string json)
    {
        var evento = JsonSerializer.Deserialize<EmpleadoEliminadoEvent>(json);
        if (evento == null) return;

        var notificacion = new Notificacion
        {
            Id = Guid.NewGuid().ToString(),
            Tipo = "DESVINCULACION",
            Destinatario = evento.Email,
            Mensaje = $"Su cuenta ha sido desactivada. Gracias por su tiempo, {evento.Nombre}.",
            FechaEnvio = DateTime.UtcNow,
            EmpleadoId = evento.Id
        };

        await GuardarNotificacion(notificacion);
    }

    private async Task ProcesarUsuarioSeguridad(string json)
    {
        var evento = JsonSerializer.Deserialize<UsuarioEvent>(json);
        if (evento == null) return;

        string mensaje = evento.Tipo switch
        {
            "usuario.creado" => evento.NeedsPasswordReset == true 
                ? $"<h2>Bienvenido a la plataforma</h2><p>Su usuario ha sido creado exitosamente con el correo electrónico: <b>{evento.Email}</b>.</p><p><b>Pasos de activación:</b></p><ol><li>Acceda al sistema de autenticación.</li><li>Utilice el siguiente token temporal para establecer su contraseña inicial:</li></ol><blockquote><b>{evento.Token}</b></blockquote>" 
                : $"<h2>Bienvenido a la plataforma</h2><p>Su usuario ha sido creado exitosamente con el correo electrónico: <b>{evento.Email}</b> y la contraseña inicial proporcionada.</p>",
            "usuario.recuperacion" => $"<h2>Recuperación de Contraseña</h2><p>Hemos recibido una solicitud de recuperación de contraseña para su cuenta (<b>{evento.Email}</b>).</p><p>Utilice este token para restablecer su contraseña:</p><blockquote><b>{evento.Token}</b></blockquote>",
            _ => "<p>Notificación de seguridad recibida.</p>"
        };

        var notificacion = new Notificacion
        {
            Id = Guid.NewGuid().ToString(),
            Tipo = "SEGURIDAD",
            Destinatario = evento.Email,
            Mensaje = mensaje,
            FechaEnvio = DateTime.UtcNow,
            EmpleadoId = evento.EmpleadoId ?? evento.Id ?? "SISTEMA"
        };

        await GuardarNotificacion(notificacion);
    }

    private async Task GuardarNotificacion(Notificacion notificacion)
    {
        using var scope = _serviceProvider.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<NotificacionesDbContext>();
        var emailService = scope.ServiceProvider.GetRequiredService<IEmailService>();

        dbContext.Notificaciones.Add(notificacion);
        await dbContext.SaveChangesAsync();

        _logger.LogInformation(
            "[NOTIFICACIÓN GUARDADA] Tipo: {Tipo} | Para: {Email} | Mensaje: {Msj}",
            notificacion.Tipo,
            notificacion.Destinatario,
            notificacion.Mensaje);

        // Enviar correo electrónico
        string subject = notificacion.Tipo switch
        {
            "SEGURIDAD" => "Notificación de Seguridad / Credenciales",
            "BIENVENIDA" => "¡Bienvenido a la empresa!",
            "DESVINCULACION" => "Aviso de desvinculación",
            "VACACIONES" => "Confirmación de Vacaciones Programadas",
            "ESTADO_CAMBIADO" => "Actualización de Estado Laboral",
            _ => "Notificación del Sistema"
        };
        
        await emailService.SendEmailAsync(notificacion.Destinatario, subject, notificacion.Mensaje);
    }

    public override async Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("[RABBITMQ] Deteniendo consumidor...");
        
        if (_channel != null)
        {
            await _channel.CloseAsync(cancellationToken);
        }
        
        if (_connection != null)
        {
            await _connection.CloseAsync(cancellationToken);
        }

        await base.StopAsync(cancellationToken);
    }
}
