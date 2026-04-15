const express = require('express');
const amqp = require('amqplib');
const jwt = require('jsonwebtoken');
const sequelize = require('./── src/config/database');
const Notification = require('./── src/models/Notification');

const app = express();
app.use(express.json());

const JWT_SECRET = process.env.JWT_SECRET || 'supersecreto';

function obtenerToken(req) {
    const authHeader = req.headers['authorization'] || '';
    if (!authHeader.startsWith('Bearer ')) {
        return null;
    }
    return authHeader.split(' ')[1];
}

function validarToken(token) {
    return jwt.verify(token, JWT_SECRET);
}

function authorize(allowedRoles) {
    return (req, res, next) => {
        const token = obtenerToken(req);
        if (!token) {
            return res.status(401).json({ success: false, message: 'Authorization header missing or malformed' });
        }
        try {
            const payload = validarToken(token);
            if (!allowedRoles.includes(payload.role)) {
                return res.status(403).json({ success: false, message: 'Permiso denegado' });
            }
            req.user = payload.sub;
            req.role = payload.role;
            next();
        } catch (err) {
            if (err.name === 'TokenExpiredError') {
                return res.status(401).json({ success: false, message: 'Token expirado' });
            }
            return res.status(401).json({ success: false, message: 'Token inválido' });
        }
    };
}

// --- ENDPOINTS REST (Solo lectura según Reto 3) ---

// Listar todas las notificaciones [cite: 77]
app.get('/notificaciones', authorize(['USER', 'ADMIN']), async (req, res) => {
    const data = await Notification.findAll();
    res.json(data);
});

// Listar por empleado específico [cite: 77]
app.get('/notificaciones/:empleadoId', authorize(['USER', 'ADMIN']), async (req, res) => {
    const data = await Notification.findAll({ where: { empleadoId: req.params.empleadoId } });
    res.json(data);
});

// --- CONSUMIDOR DE EVENTOS (RabbitMQ) ---

async function startRabbitMQ() {
    try {
        const connection = await amqp.connect(process.env.RABBITMQ_URL);
        const channel = await connection.createChannel();
        
        // Usamos fanout para que el evento llegue a Perfiles y Notificaciones a la vez [cite: 12]
        const empleadoExchange = 'empleados_events';
        const usuarioExchange = 'usuario_events';
        await channel.assertExchange(empleadoExchange, 'fanout', { durable: true });
        await channel.assertExchange(usuarioExchange, 'fanout', { durable: true });
        
        const q = await channel.assertQueue('notificaciones_queue', { durable: true });
        await channel.bindQueue(q.queue, empleadoExchange, '');
        await channel.bindQueue(q.queue, usuarioExchange, '');

        console.log(" [*] Esperando eventos en notificaciones-service...");

        channel.consume(q.queue, async (msg) => {
            if (msg !== null) {
                const eventData = JSON.parse(msg.content.toString());
                const eventType = eventData.tipo;

                let tipo = "";
                let msj = "";

                if (eventType === 'empleado.creado') {
                    tipo = 'BIENVENIDA';
                    msj = `Bienvenido ${eventData.nombre}`;
                } else if (eventType === 'empleado.eliminado') {
                    tipo = 'DESVINCULACION';
                    msj = `Su cuenta ha sido desactivada para ${eventData.nombre}`;
                } else if (eventType === 'usuario.creado' || eventType === 'usuario.recuperacion') {
                    tipo = 'SEGURIDAD';
                    msj = `Para establecer o recuperar su contraseña, utilice el token: ${eventData.token}`;
                }

                if (tipo) {
                    console.log(`[NOTIFICACIÓN] Tipo: ${tipo} | Para: ${eventData.email} | Mensaje: ${msj}`);

                    try {
                        await Notification.create({
                            tipo: tipo,
                            destinatario: eventData.email,
                            mensaje: msj,
                            empleadoId: eventData.id || eventData.empleadoId || null
                        });
                    } catch (err) {
                        console.error("Error creando notificación:", err);
                    }
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
sequelize.sync({ alter: true }).then(() => {
    console.log("PostgreSQL Conectado");
    app.listen(PORT, () => {
        console.log(`Servicio de Notificaciones en puerto ${PORT}`);
        startRabbitMQ();
    });
});