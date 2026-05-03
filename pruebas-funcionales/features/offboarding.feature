# language: es
Característica: Escenarios de Offboarding
  Como administrador del sistema
  Quiero desvincular empleados del sistema
  Para revocar su acceso y mantener la seguridad

  Antecedentes:
    Dado que el sistema está operativo

  Escenario: Desvinculación completa de un empleado
    Dado que existe un empleado activo con nombre "Pedro Picapiedra" y email "pedro.p@bedrock.com"
    Cuando el administrador elimina al empleado recién creado
    Entonces el sistema responde con un código de estado 200
    Y el empleado desvinculado intenta iniciar sesión
    Entonces el sistema responde con un código de estado 401
