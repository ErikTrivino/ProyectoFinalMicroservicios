# language: es
Característica: Seguridad y Control de Acceso (RBAC)
  Como oficial de seguridad
  Quiero validar las reglas de acceso
  Para proteger la información de los empleados

  Antecedentes:
    Dado que el sistema está operativo

  Escenario: Acceso denegado sin token
    Dado que no tengo un token de autenticación
    Cuando intento consultar la lista de empleados
    Entonces el sistema responde con un código de estado 401

  Escenario: Acceso denegado con token inválido
    Dado que tengo un token inválido
    Cuando intento consultar la lista de empleados
    Entonces el sistema responde con un código de estado 401

  Escenario: Rol USER tiene permisos de solo lectura
    Dado que estoy autenticado como "USER"
    Cuando intento consultar la lista de empleados
    Entonces el sistema responde con un código de estado 200

  Escenario: Rol ADMIN tiene acceso total
    Dado que estoy autenticado como "ADMIN"
    Cuando intento consultar la lista de empleados
    Entonces el sistema responde con un código de estado 200
