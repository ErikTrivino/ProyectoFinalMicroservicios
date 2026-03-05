const express = require('express');
const amqp = require('amqplib');
const sequelize = require('./config/database');
const Notification = require('./models/Notification');

const app = express();
app.use(express.json());

// --- ENDPOINTS REST (Solo lectura según Reto 3) ---

// Listar todas las notificaciones [cite: 77]
app.get('/notificaciones', async (req, res) => {
    const data = await Notification.findAll();
    res.json(data);
});

// Listar por empleado específico [cite: 77]
app.get('/notificaciones/:empleadoId', async (req, res) => {
    const data = await Notification.findAll({ where: { empleadoId: req.params.empleadoId } });
    res.json(data);
});

// --- CONSUMIDOR DE EVENTOS (RabbitMQ) ---

async function startRabbitMQ() {
    try {
        const connection = await amqp.connect(process.env.RABBITMQ_URL);
        const channel = await connection.createChannel();
        
        // Usamos fanout para que el evento llegue a Perfiles y Notificaciones a la vez [cite: 12]
        const exchange = 'empleado_events';
        await channel.assertExchange(exchange, 'fanout', { durable: true });
        
        const q = await channel.assertQueue('notificaciones_queue', { durable: true });
        await channel.bindQueue(q.queue, exchange, '');

        console.log(" [*] Esperando eventos en notificaciones-service...");

        channel.consume(q.queue, async (msg) => {
            if (msg !== null) {
                const eventData = JSON.parse(msg.content.toString());
                const eventType = msg.properties.type; // "empleado.creado" o "empleado.eliminado" [cite: 55]

                let tipo = "";
                let msj = "";

                if (eventType === 'empleado.creado') {
                    tipo = 'BIENVENIDA';
                    msj = `Bienvenido ${eventData.nombre}`;
                } else if (eventType === 'empleado.eliminado') {
                    tipo = 'DESVINCULACION';
                    msj = `Su cuenta ha sido desactivada para ${eventData.nombre}`;
                }

                if (tipo) {
                    // 1. Simulación por log (Requisito) [cite: 73, 74]
                    console.log(`[NOTIFICACIÓN] Tipo: ${tipo} | Para: ${eventData.email} | Mensaje: ${msj}`);

                    // 2. Persistencia en Postgres [cite: 89]
                    await Notification.create({
                        tipo: tipo,
                        destinatario: eventData.email,
                        mensaje: msj,
                        empleadoId: eventData.id
                    });
                }
                channel.ack(msg);
            }
        });
    } catch (error) {
        console.error("RabbitMQ Error:", error);
        setTimeout(startRabbitMQ, 5000); // Reintento si el broker no está listo
    }
}

// --- ARRANQUE DEL SERVICIO ---
const PORT = process.env.PORT || 8084;

// Sincronizar DB y encender servidor
sequelize.sync().then(() => {
    console.log("PostgreSQL Conectado");
    app.listen(PORT, () => {
        console.log(`Servicio de Notificaciones en puerto ${PORT}`);
        startRabbitMQ();
    });
});