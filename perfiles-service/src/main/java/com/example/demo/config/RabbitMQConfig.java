package com.example.demo.config;


import org.springframework.amqp.core.*;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMQConfig {

    // Nombre del exchange (debe coincidir con el de Python)
    public static final String EXCHANGE_EMPLEADOS = "empleados_events";

    // Cola exclusiva de este servicio
    public static final String QUEUE_PERFILES_CREADO = "perfiles.empleado.creado";

    // 1. Declarar el exchange fanout
    @Bean
    public FanoutExchange empleadosExchange() {
        return new FanoutExchange(EXCHANGE_EMPLEADOS, true, false);
    }

    // 2. Declarar la cola
    @Bean
    public Queue perfilesEmpleadoCreadoQueue() {
        return QueueBuilder.durable(QUEUE_PERFILES_CREADO).build();
    }

    // 3. Binding: conectar la cola al exchange
    @Bean
    public Binding bindingPerfilesCreadoQueue(
            Queue perfilesEmpleadoCreadoQueue,
            FanoutExchange empleadosExchange) {
        return BindingBuilder
                .bind(perfilesEmpleadoCreadoQueue)
                .to(empleadosExchange);
    }

    // 4. Converter JSON para deserializar los mensajes
    @Bean
    public MessageConverter jsonMessageConverter(com.fasterxml.jackson.databind.ObjectMapper objectMapper) {
        return new Jackson2JsonMessageConverter(objectMapper);
    }
}