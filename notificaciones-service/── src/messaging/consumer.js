const amqp = require('amqplib');
const Notification = require('../models/Notification');

async function consumeEvents() {
    try {
        // Conexión al broker usando variable de entorno [cite: 90]
        const connection = await amqp.connect(process.env.RABBITMQ_URL || 'amqp://admin:admin@message-broker:5672');
        const channel = await connection.createChannel();
        
        // Declaramos el exchange de tipo 'fanout' para el patrón requerido [cite: 12]
        const exchange = 'empleados_events';
        await channel.assertExchange(exchange, 'fanout', { durable: true });

        // Cola exclusiva para este servicio
        const q = await channel.assertQueue('notificaciones_queue', { exclusive: false });
        await channel.bindQueue(q.queue, exchange, '');

        console.log(" [*] Esperando eventos en %s.", q.queue);

        channel.consume(q.queue, async (msg) => {
            if (msg !== null) {
                const eventData = JSON.parse(msg.content.toString());
                const routingKey = msg.fields.routingKey; // O basado en un campo del JSON

                console.log(" [x] Evento recibido: %s", msg.content.toString());

                let notificationBody = {};

                // Lógica según el tipo de evento [cite: 71, 74]
                if (eventData.tipo === 'empleado.creado') {
                    notificationBody = {
                        tipo: 'BIENVENIDA',
                        destinatario: eventData.email,
                        mensaje: `Bienvenido ${eventData.nombre}`,
                        empleadoId: eventData.id
                    };
                } else if (eventData.tipo === 'empleado.eliminado') {
                    notificationBody = {
                        tipo: 'DESVINCULACION',
                        destinatario: eventData.email,
                        mensaje: `Su cuenta ha sido desactivada`,
                        empleadoId: eventData.id
                    };
                }

                // Persistir en DB [cite: 76, 89]
                const newNotification = new Notification(notificationBody);
                await newNotification.save();
                
                // Simulación en log [cite: 73, 74]
                console.log(`[NOTIFICACIÓN] Tipo: ${notificationBody.tipo} | Para: ${notificationBody.destinatario} | Mensaje: ${notificationBody.mensaje}`);

                channel.ack(msg); // Confirmar procesamiento del mensaje
            }
        });
    } catch (error) {
        console.error("Error en el consumidor de eventos:", error);
    }
}

module.exports = { consumeEvents };