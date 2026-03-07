package com.example.demo.config;


import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class SwaggerConfig {

    @Bean
    public OpenAPI perfilesOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("API Perfiles")
                        .description("Servicio de Gestion de Perfiles - Reto 3 Microservicios")
                        .version("1.0.0"));
    }
}