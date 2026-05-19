package com.example.demo.dto;


import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

// DTO que representa el evento que viene del broker
// Los campos coinciden con lo que publica Python
@JsonIgnoreProperties(ignoreUnknown = true)
public class EmpleadoCreadoEvent {

    private String id;             // ID del empleado
    private String nombre;
    private String email;
    private String departamentoId;
    private String fechaIngreso;

    // Constructor vacio (requerido por Jackson)
    public EmpleadoCreadoEvent() {}

    // --- Getters y Setters ---
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getNombre() { return nombre; }
    public void setNombre(String nombre) { this.nombre = nombre; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getDepartamentoId() { return departamentoId; }
    public void setDepartamentoId(String departamentoId) { this.departamentoId = departamentoId; }

    public String getFechaIngreso() { return fechaIngreso; }
    public void setFechaIngreso(String fechaIngreso) { this.fechaIngreso = fechaIngreso; }

    @Override
    public String toString() {
        return "EmpleadoCreadoEvent{id='" + id + "', nombre='" + nombre + "', email='" + email + "'}";
    }
}