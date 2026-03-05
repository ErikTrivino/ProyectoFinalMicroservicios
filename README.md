# ProyectoFinalMicroservicios
Sistema de gestión de empleados
Integrantes
Erik Pablo Triviño Gonzalez
Felip Valencia Londoño
Anderson Betancurt
Jose Felipe Gabinos..

📄 Justificación del Message Broker: RabbitMQPor qué elegimos RabbitMQ sobre las alternativasPara el sistema de Onboarding y Offboarding, se ha seleccionado RabbitMQ por las siguientes razones técnicas:Soporte Nativo del Patrón Fan-out: El reto exige que un solo evento (ej. empleado.creado) dispare acciones en múltiples servicios independientes (Notificaciones y Perfiles). RabbitMQ implementa esto de forma nativa y sencilla mediante Exchanges de tipo fanout.Garantía de Entrega (Protocolo AMQP): A diferencia de opciones más ligeras, RabbitMQ utiliza el protocolo AMQP que asegura que los mensajes no se pierdan si un servicio (como el de Notificaciones) está temporalmente caído.Facilidad de Administración: Incluye una interfaz web de gestión (Management UI) que permite visualizar en tiempo real el estado de las colas, los consumidores y el flujo de eventos, lo cual es un requisito explícito del reto.Curva de Aprendizaje y Madurez: Comparado con Apache Kafka, que está diseñado para streaming de datos masivos y tiene una configuración mucho más compleja, RabbitMQ es ideal para la comunicación entre microservicios de propósito general.Ligereza frente a NATS/Redis: Aunque NATS es más rápido y Redis Streams es más ligero, RabbitMQ ofrece una gestión de errores y reintentos (dead-letter exchanges) más robusta para procesos críticos como el registro de empleados.