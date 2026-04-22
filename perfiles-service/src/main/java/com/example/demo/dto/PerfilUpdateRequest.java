package com.example.demo.dto;


// DTO para la actualizacion parcial del perfil via PUT
public class PerfilUpdateRequest {

    private String telefono;
    private String direccion;
    private String ciudad;
    private String biografia;

    public PerfilUpdateRequest() {}

    public String getTelefono() { return telefono; }
    public void setTelefono(String telefono) { this.telefono = telefono; }

    public String getDireccion() { return direccion; }
    public void setDireccion(String direccion) { this.direccion = direccion; }

    public String getCiudad() { return ciudad; }
    public void setCiudad(String ciudad) { this.ciudad = ciudad; }

    public String getBiografia() { return biografia; }
    public void setBiografia(String biografia) { this.biografia = biografia; }
}