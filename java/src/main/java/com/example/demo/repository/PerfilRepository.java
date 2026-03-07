package com.example.demo.repository;

import com.example.demo.model.Perfil;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface PerfilRepository extends JpaRepository<Perfil, String> {

    // Spring Data genera el query automaticamente por el nombre del metodo
    Optional<Perfil> findByEmpleadoId(String empleadoId);

    // Verificar si ya existe un perfil para un empleado
    boolean existsByEmpleadoId(String empleadoId);
}