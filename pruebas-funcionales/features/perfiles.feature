# language: es
Característica: Gestión de Perfiles de Empleados
  Como administrador o empleado
  Quiero gestionar la información de los perfiles
  Para mantener actualizada la experiencia y biografía de los colaboradores

  Antecedentes:
    Dado que el sistema está operativo

  Escenario: Listar todos los perfiles como administrador
    Dado que estoy autenticado como "ADMIN"
    Cuando intento consultar la lista de perfiles
    Entonces el sistema responde con un código de estado 200
    Y la respuesta contiene una lista de perfiles

  Escenario: Consultar perfil de un empleado específico
    Dado que estoy autenticado como "ADMIN"
    Y que existe un empleado activo con nombre "Carlos Perfil" y email "carlos.perfil@example.com"
    Cuando intento consultar el perfil del empleado recién creado
    Entonces el sistema responde con un código de estado 200
    Y los detalles del perfil corresponden al empleado creado

  Escenario: Actualizar biografía y experiencia de un perfil
    Dado que estoy autenticado como "ADMIN"
    Y que existe un empleado activo con nombre "Elena Update" y email "elena.update@example.com"
    Cuando actualizo el perfil del empleado con biografía "Experta en microservicios" y experiencia "5 años"
    Entonces el sistema responde con un código de estado 200
    Y el perfil actualizado muestra la nueva biografía y experiencia
