package com.example.demo.model;


import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;


@Entity
@Getter
@Setter
@AllArgsConstructor
@Builder
@ToString
@Table(name = "perfiles")
public class Perfil {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String id;

    @Column(name = "empleado_id", unique = true, nullable = false)
    private String empleadoId;

    @Column(nullable = false)
    private String nombre;

    @Column(nullable = false)
    private String email;

    @Column(columnDefinition = "VARCHAR(20) DEFAULT ''")
    private String telefono = "";

    @Column(columnDefinition = "VARCHAR(255) DEFAULT ''")
    private String direccion = "";

    @Column(columnDefinition = "VARCHAR(100) DEFAULT ''")
    private String ciudad = "";

    @Column(columnDefinition = "TEXT DEFAULT ''")
    private String biografia = "";

    @Column(name = "fecha_creacion", nullable = false)
    private LocalDateTime fechaCreacion;

    public Perfil() {}

    // --- Constructor para crear desde evento ---
    public Perfil(String empleadoId, String nombre, String email) {
        this.empleadoId = empleadoId;
        this.nombre = nombre;
        this.email = email;
        this.telefono = "";
        this.direccion = "";
        this.ciudad = "";
        this.biografia = "";
        this.fechaCreacion = LocalDateTime.now();
    }


}