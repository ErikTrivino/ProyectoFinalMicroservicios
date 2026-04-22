package com.example.demo.service;




import com.example.demo.dto.EmpleadoCreadoEvent;
import com.example.demo.dto.PerfilUpdateRequest;
import com.example.demo.model.Perfil;
import com.example.demo.repository.PerfilRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class PerfilService {

    private final PerfilRepository perfilRepository;

    // Inyeccion de dependencias por constructor
    public PerfilService(PerfilRepository perfilRepository) {
        this.perfilRepository = perfilRepository;
    }

    /**
     * Crea un perfil por defecto a partir de un evento de empleado creado.
     * Si ya existe un perfil para ese empleado, no lo duplica.
     */
    public Perfil crearPerfilPorDefecto(EmpleadoCreadoEvent evento) {
        // Verificar que no exista ya
        if (perfilRepository.existsByEmpleadoId(evento.getId())) {
            System.out.println("[PERFIL] Ya existe perfil para empleado: " + evento.getId());
            return perfilRepository.findByEmpleadoId(evento.getId()).orElse(null);
        }

        Perfil perfil = new Perfil(
                evento.getId(),
                evento.getNombre(),
                evento.getEmail()
        );

        Perfil guardado = perfilRepository.save(perfil);
        System.out.println("[PERFIL] Creado perfil por defecto para: " + evento.getNombre());
        return guardado;
    }

    /**
     * Busca un perfil por el ID del empleado.
     */
    public Optional<Perfil> buscarPorEmpleadoId(String empleadoId) {
        return perfilRepository.findByEmpleadoId(empleadoId);
    }

    /**
     * Lista todos los perfiles.
     */
    public List<Perfil> listarTodos() {
        return perfilRepository.findAll();
    }

    /**
     * Actualiza los campos editables del perfil.
     */
    public Optional<Perfil> actualizarPerfil(String empleadoId, PerfilUpdateRequest request) {
        return perfilRepository.findByEmpleadoId(empleadoId)
                .map(perfil -> {
                    if (request.getTelefono() != null) perfil.setTelefono(request.getTelefono());
                    if (request.getDireccion() != null) perfil.setDireccion(request.getDireccion());
                    if (request.getCiudad() != null) perfil.setCiudad(request.getCiudad());
                    if (request.getBiografia() != null) perfil.setBiografia(request.getBiografia());
                    return perfilRepository.save(perfil);
                });
    }

    /**
     * Elimina un perfil por el ID del empleado.
     */
    public boolean eliminarPerfil(String empleadoId) {
        return perfilRepository.findByEmpleadoId(empleadoId)
                .map(perfil -> {
                    perfilRepository.delete(perfil);
                    System.out.println("[PERFIL] Eliminado perfil de empleado: " + empleadoId);
                    return true;
                }).orElse(false);
    }
}