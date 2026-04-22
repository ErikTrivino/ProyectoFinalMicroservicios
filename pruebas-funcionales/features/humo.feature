# language: es
Característica: Prueba de Humo
  Como desarrollador
  Quiero verificar que el sistema responde
  Para asegurar que la infraestructura está arriba

  Escenario: Verificar respuesta del sistema
    Dado que el sistema está operativo
    Cuando intento consultar la lista de empleados
    Entonces el sistema responde con un código de estado 401
