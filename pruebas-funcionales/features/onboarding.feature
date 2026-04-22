# language: es
Característica: Onboarding con Verificación Asincrónica
  Como administrador del sistema
  Quiero registrar nuevos empleados y que reciban sus credenciales
  Para que puedan acceder al sistema de forma segura

  Antecedentes:
    Dado que el sistema está operativo

  Escenario: Registro exitoso de un nuevo empleado
    Cuando el administrador registra un nuevo empleado con nombre "Carlos Ruiz" y email "carlos.ruiz@test.com"
    Y espero la notificación y activo la cuenta con la nueva contraseña "SecurePass123"
    Y el nuevo empleado intenta iniciar sesión
    Entonces el sistema responde con un código de estado 200
    Y la respuesta debe contener un token de acceso

  Escenario: Validación de datos inválidos en el registro
    Cuando intento registrar un empleado con datos inválidos
    Entonces el sistema responde con un código de estado 400
