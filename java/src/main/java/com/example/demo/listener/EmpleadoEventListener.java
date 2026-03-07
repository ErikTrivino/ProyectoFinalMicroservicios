package com.example.demo.listener;


import com.example.demo.config.RabbitMQConfig;
import com.example.demo.dto.EmpleadoCreadoEvent;
import com.example.demo.service.PerfilService;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

@Component
public class EmpleadoEventListener {

    private final PerfilService perfilService;

    public EmpleadoEventListener(PerfilService perfilService) {
        this.perfilService = perfilService;
    }

    /**
     * Escucha eventos de empleado.creado desde RabbitMQ.
     * Cuando llega un evento, crea automaticamente un perfil por defecto.
     *
     * La anotacion @RabbitListener hace toda la magia:
     * - Se suscribe a la cola definida en RabbitMQConfig
     * - Deserializa el JSON a EmpleadoCreadoEvent automaticamente
     * - Llama a este metodo cada vez que llega un mensaje
     */
    @RabbitListener(queues = RabbitMQConfig.QUEUE_PERFILES_CREADO)
    public void onEmpleadoCreado(EmpleadoCreadoEvent evento) {
        System.out.println("[LISTENER] Evento recibido: empleado.creado -> " + evento);

        try {
            perfilService.crearPerfilPorDefecto(evento);
            System.out.println("[LISTENER] Perfil creado exitosamente para: " + evento.getNombre());
        } catch (Exception e) {
            System.err.println("[LISTENER] Error procesando evento: " + e.getMessage());
        }
    }
}