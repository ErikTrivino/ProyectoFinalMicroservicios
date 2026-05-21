package com.example.demo.controller;


import com.example.demo.config.JwtUtils;
import com.example.demo.dto.PerfilUpdateRequest;
import com.example.demo.model.Perfil;
import com.example.demo.service.PerfilService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/perfiles")
@Tag(name = "Perfiles", description = "Gestion de perfiles de empleados")
public class PerfilController {

    private final PerfilService perfilService;
    private final JwtUtils jwtUtils;

    public PerfilController(PerfilService perfilService, JwtUtils jwtUtils) {
        this.perfilService = perfilService;
        this.jwtUtils = jwtUtils;
    }

    @GetMapping
    @PreAuthorize("hasRole('ADMIN') or hasRole('USER')")
    @Operation(summary = "Listar todos los perfiles")
    public ResponseEntity<Map<String, Object>> listarPerfiles() {
        List<Perfil> perfiles = perfilService.listarTodos();

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Lista de perfiles");
        response.put("data", perfiles);

        return ResponseEntity.ok(response);
    }

    @GetMapping("/{empleadoId}")
    @PreAuthorize("hasRole('ADMIN') or hasRole('USER')")
    @Operation(summary = "Consultar perfil por ID de empleado")
    public ResponseEntity<Map<String, Object>> obtenerPerfil(
            @PathVariable String empleadoId) {

        return perfilService.buscarPorEmpleadoId(empleadoId)
                .map(perfil -> {
                    Map<String, Object> response = new HashMap<>();
                    response.put("success", true);
                    response.put("message", "Perfil encontrado");
                    response.put("data", perfil);
                    return ResponseEntity.ok(response);
                })
                .orElseGet(() -> {
                    Map<String, Object> response = new HashMap<>();
                    response.put("success", false);
                    response.put("message", "Perfil no encontrado para empleado: " + empleadoId);
                    response.put("data", null);
                    return ResponseEntity.status(404).body(response);
                });
    }

    @PutMapping("/{empleadoId}")
    @PreAuthorize("hasRole('ADMIN') or hasRole('USER')")
    @Operation(summary = "Actualizar perfil de un empleado")
    public ResponseEntity<Map<String, Object>> actualizarPerfil(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @PathVariable String empleadoId,
            @RequestBody PerfilUpdateRequest request) {

        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String token = authHeader.substring(7);
            if (jwtUtils.isTokenValid(token)) {
                String reqRole = jwtUtils.extractRole(token);
                String reqEmpId = jwtUtils.extractEmpleadoId(token);

                if ("USER".equalsIgnoreCase(reqRole) && !empleadoId.equals(reqEmpId)) {
                    Map<String, Object> response = new HashMap<>();
                    response.put("success", false);
                    response.put("message", "Permiso denegado: No es dueno de este perfil.");
                    response.put("data", null);
                    return ResponseEntity.status(403).body(response);
                }
            }
        }

        return perfilService.actualizarPerfil(empleadoId, request)
                .map(perfil -> {
                    Map<String, Object> response = new HashMap<>();
                    response.put("success", true);
                    response.put("message", "Perfil actualizado");
                    response.put("data", perfil);
                    return ResponseEntity.ok(response);
                })
                .orElseGet(() -> {
                    Map<String, Object> response = new HashMap<>();
                    response.put("success", false);
                    response.put("message", "Perfil no encontrado para empleado: " + empleadoId);
                    response.put("data", null);
                    return ResponseEntity.status(404).body(response);
                });
    }
}
