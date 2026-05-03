package com.example.demo.listener;

import com.example.demo.config.RabbitMQConfig;
import com.example.demo.dto.EmpleadoCreadoEvent;
import com.example.demo.dto.EmpleadoEliminadoEvent;
import com.example.demo.service.PerfilService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

@Component
public class EmpleadoEventListener {

    private final PerfilService perfilService;
    private final ObjectMapper objectMapper;

    public EmpleadoEventListener(PerfilService perfilService, ObjectMapper objectMapper) {
        this.perfilService = perfilService;
        this.objectMapper = objectMapper;
    }

    /**
     * Escucha eventos desde la cola de perfiles.
     * Detecta el tipo de evento (creado o eliminado) y actúa en consecuencia.
     */
    @RabbitListener(queues = RabbitMQConfig.QUEUE_PERFILES_CREADO)
    public void onMessage(Message message) {
        String eventType = message.getMessageProperties().getType();
        byte[] body = message.getBody();
        
        System.out.println("[LISTENER] Mensaje recibido de tipo: " + eventType);

        try {
            if ("empleado.creado".equals(eventType)) {
                EmpleadoCreadoEvent evento = objectMapper.readValue(body, EmpleadoCreadoEvent.class);
                perfilService.crearPerfilPorDefecto(evento);
                System.out.println("[LISTENER] Perfil creado exitosamente para: " + evento.getNombre());
            } 
            else if ("empleado.eliminado".equals(eventType)) {
                EmpleadoEliminadoEvent evento = objectMapper.readValue(body, EmpleadoEliminadoEvent.class);
                perfilService.eliminarPerfil(evento.getId());
                System.out.println("[LISTENER] Perfil eliminado exitosamente para: " + evento.getNombre());
            }
            else {
                System.out.println("[LISTENER] Tipo de evento no procesado por este servicio: " + eventType);
            }
        } catch (Exception e) {
            System.err.println("[LISTENER] Error procesando evento " + eventType + ": " + e.getMessage());
        }
    }
}