package com.example.demo.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.connection.Connection;

import java.util.HashMap;
import java.util.Map;

@RestController
public class HealthController {

    private final JdbcTemplate jdbcTemplate;
    private final ConnectionFactory rabbitConnectionFactory;

    public HealthController(JdbcTemplate jdbcTemplate, ConnectionFactory rabbitConnectionFactory) {
        this.jdbcTemplate = jdbcTemplate;
        this.rabbitConnectionFactory = rabbitConnectionFactory;
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> response = new HashMap<>();
        Map<String, Object> dependencies = new HashMap<>();
        boolean dbOk = false;
        boolean rabbitOk = false;

        try {
            jdbcTemplate.execute("SELECT 1");
            dbOk = true;
            Map<String, String> dbStatus = new HashMap<>();
            dbStatus.put("status", "UP");
            dependencies.put("database", dbStatus);
        } catch (Exception e) {
            Map<String, String> dbStatus = new HashMap<>();
            dbStatus.put("status", "DOWN");
            dbStatus.put("error", e.getMessage());
            dependencies.put("database", dbStatus);
        }

        try {
            Connection conn = rabbitConnectionFactory.createConnection();
            conn.close();
            rabbitOk = true;
            Map<String, String> rabbitStatus = new HashMap<>();
            rabbitStatus.put("status", "UP");
            dependencies.put("rabbitmq", rabbitStatus);
        } catch (Exception e) {
            Map<String, String> rabbitStatus = new HashMap<>();
            rabbitStatus.put("status", "DOWN");
            rabbitStatus.put("error", e.getMessage());
            dependencies.put("rabbitmq", rabbitStatus);
        }

        String overallStatus = (dbOk) ? "UP" : "DOWN";
        response.put("status", overallStatus);
        response.put("dependencies", dependencies);

        if (dbOk) {
            return ResponseEntity.ok(response);
        } else {
            return ResponseEntity.status(500).body(response);
        }
    }
}
