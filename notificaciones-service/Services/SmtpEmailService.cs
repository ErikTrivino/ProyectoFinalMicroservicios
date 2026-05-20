using System.Net;
using System.Net.Mail;

namespace NotificacionesService.Services;

public class SmtpEmailService : IEmailService
{
    private readonly IConfiguration _configuration;
    private readonly ILogger<SmtpEmailService> _logger;

    public SmtpEmailService(IConfiguration configuration, ILogger<SmtpEmailService> logger)
    {
        _configuration = configuration;
        _logger = logger;
    }

    public async Task SendEmailAsync(string to, string subject, string body)
    {
        try
        {
            var host = _configuration["Smtp:Host"] ?? "smtp.mailtrap.io";
            var port = int.Parse(_configuration["Smtp:Port"] ?? "2525");
            var user = _configuration["Smtp:Username"] ?? "";
            var pass = _configuration["Smtp:Password"] ?? "";
            var from = _configuration["Smtp:From"] ?? "no-reply@empresa.com";
            var enableSsl = bool.Parse(_configuration["Smtp:EnableSsl"] ?? "true");

            using var client = new SmtpClient(host, port)
            {
                EnableSsl = enableSsl
            };

            if (!string.IsNullOrEmpty(user) && !string.IsNullOrEmpty(pass))
            {
                client.Credentials = new NetworkCredential(user, pass);
            }

            var mailMessage = new MailMessage(from, to, subject, body)
            {
                IsBodyHtml = true
            };

            await client.SendMailAsync(mailMessage);
            _logger.LogInformation("[EMAIL] Correo enviado a {To} con asunto '{Subject}'", to, subject);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[EMAIL] Error enviando correo a {To}", to);
            // No lanzar excepción para no detener el proceso
        }
    }
}
