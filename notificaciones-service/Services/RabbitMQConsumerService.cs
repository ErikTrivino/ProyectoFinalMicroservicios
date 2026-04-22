using System.Text;
using System.Text.Json;
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using NotificacionesService.Data;
using NotificacionesService.DTOs;
using NotificacionesService.Models;

namespace NotificacionesService.Services;

/// <summary>
/// Servicio en background que consume eventos de RabbitMQ
/// Escucha los eventos empleado.creado y empleado.eliminado
/// </summary>
public class RabbitMQConsumerService : BackgroundService
{
    private readonly ILogger<RabbitMQConsumerService> _logger;
    private readonly IServiceProvider _serviceProvider;
    private readonly IConfiguration _configuration;
    
    private IConnection? _connection;
    private IChannel? _channel;

    // Exchanges (deben coincidir con los de Python)
    private const string EXCHANGE_EMPLEADO_CREADO = "empleado.creado";
    private const string EXCHANGE_EMPLEADO_ELIMINADO = "empleado.eliminado";

    // Colas exclusivas de este servicio
    private const string QUEUE_NOTIF_CREADO = "notificaciones.empleado.creado";
    private const string QUEUE_NOTIF_ELIMINADO = "notificaciones.empleado.eliminado";

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
        _logger.LogInformation("[RABBITMQ] Iniciando consumidor de eventos...");

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

        var maxRetries = 10;
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

        // Declarar exchanges tipo fanout (igual que en Python y Java)
        await _channel.ExchangeDeclareAsync(EXCHANGE_EMPLEADO_CREADO, ExchangeType.Fanout, durable: true);
        await _channel.ExchangeDeclareAsync(EXCHANGE_EMPLEADO_ELIMINADO, ExchangeType.Fanout, durable: true);

        // Declarar colas
        await _channel.QueueDeclareAsync(QUEUE_NOTIF_CREADO, durable: true, exclusive: false, autoDelete: false);
        await _channel.QueueDeclareAsync(QUEUE_NOTIF_ELIMINADO, durable: true, exclusive: false, autoDelete: false);

        // Binding: conectar colas a exchanges
        await _channel.QueueBindAsync(QUEUE_NOTIF_CREADO, EXCHANGE_EMPLEADO_CREADO, string.Empty);
        await _channel.QueueBindAsync(QUEUE_NOTIF_ELIMINADO, EXCHANGE_EMPLEADO_ELIMINADO, string.Empty);

        // Configurar consumidores
        var consumerCreado = new AsyncEventingBasicConsumer(_channel);
        consumerCreado.ReceivedAsync += OnEmpleadoCreadoReceived;
        await _channel.BasicConsumeAsync(QUEUE_NOTIF_CREADO, autoAck: false, consumer: consumerCreado);

        var consumerEliminado = new AsyncEventingBasicConsumer(_channel);
        consumerEliminado.ReceivedAsync += OnEmpleadoEliminadoReceived;
        await _channel.BasicConsumeAsync(QUEUE_NOTIF_ELIMINADO, autoAck: false, consumer: consumerEliminado);

        _logger.LogInformation("[RABBITMQ] Consumidores configurados. Escuchando eventos...");
    }

    private async Task OnEmpleadoCreadoReceived(object sender, BasicDeliverEventArgs ea)
    {
        try
        {
            var body = ea.Body.ToArray();
            var json = Encoding.UTF8.GetString(body);
            
            _logger.LogInformation("[EVENTO] Recibido empleado.creado: {Json}", json);

            var evento = JsonSerializer.Deserialize<EmpleadoCreadoEvent>(json);
            if (evento == null)
            {
                _logger.LogWarning("[EVENTO] No se pudo deserializar el evento empleado.creado");
                await _channel!.BasicAckAsync(ea.DeliveryTag, false);
                return;
            }

            // Crear notificación de bienvenida
            var notificacion = new Notificacion
            {
                Id = Guid.NewGuid().ToString(),
                Tipo = "BIENVENIDA",
                Destinatario = evento.Email,
                Mensaje = $"Bienvenido {evento.Nombre} a la empresa. Tu cuenta ha sido creada exitosamente.",
                FechaEnvio = DateTime.UtcNow,
                EmpleadoId = evento.Id
            };

            // Guardar en BD
            using var scope = _serviceProvider.CreateScope();
            var dbContext = scope.ServiceProvider.GetRequiredService<NotificacionesDbContext>();
            dbContext.Notificaciones.Add(notificacion);
            await dbContext.SaveChangesAsync();

            // Simular envío de notificación (log estructurado)
            _logger.LogInformation(
                "[NOTIFICACIÓN] Tipo: {Tipo} | Para: {Email} | Mensaje: \"{Mensaje}\"",
                notificacion.Tipo,
                notificacion.Destinatario,
                notificacion.Mensaje);

            await _channel!.BasicAckAsync(ea.DeliveryTag, false);
            _logger.LogInformation("[EVENTO] Notificación de bienvenida registrada para: {Nombre}", evento.Nombre);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[EVENTO] Error procesando empleado.creado");
            await _channel!.BasicNackAsync(ea.DeliveryTag, false, true);
        }
    }

    private async Task OnEmpleadoEliminadoReceived(object sender, BasicDeliverEventArgs ea)
    {
        try
        {
            var body = ea.Body.ToArray();
            var json = Encoding.UTF8.GetString(body);
            
            _logger.LogInformation("[EVENTO] Recibido empleado.eliminado: {Json}", json);

            var evento = JsonSerializer.Deserialize<EmpleadoEliminadoEvent>(json);
            if (evento == null)
            {
                _logger.LogWarning("[EVENTO] No se pudo deserializar el evento empleado.eliminado");
                await _channel!.BasicAckAsync(ea.DeliveryTag, false);
                return;
            }

            // Crear notificación de desvinculación
            var notificacion = new Notificacion
            {
                Id = Guid.NewGuid().ToString(),
                Tipo = "DESVINCULACION",
                Destinatario = evento.Email,
                Mensaje = $"Su cuenta ha sido desactivada. Gracias por su tiempo en la empresa, {evento.Nombre}.",
                FechaEnvio = DateTime.UtcNow,
                EmpleadoId = evento.Id
            };

            // Guardar en BD
            using var scope = _serviceProvider.CreateScope();
            var dbContext = scope.ServiceProvider.GetRequiredService<NotificacionesDbContext>();
            dbContext.Notificaciones.Add(notificacion);
            await dbContext.SaveChangesAsync();

            // Simular envío de notificación (log estructurado)
            _logger.LogInformation(
                "[NOTIFICACIÓN] Tipo: {Tipo} | Para: {Email} | Mensaje: \"{Mensaje}\"",
                notificacion.Tipo,
                notificacion.Destinatario,
                notificacion.Mensaje);

            await _channel!.BasicAckAsync(ea.DeliveryTag, false);
            _logger.LogInformation("[EVENTO] Notificación de desvinculación registrada para: {Nombre}", evento.Nombre);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[EVENTO] Error procesando empleado.eliminado");
            await _channel!.BasicNackAsync(ea.DeliveryTag, false, true);
        }
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
