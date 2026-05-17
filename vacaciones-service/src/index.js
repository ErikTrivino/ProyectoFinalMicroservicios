require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { initDB } = require('./config/db');
const rabbitMQ = require('./config/rabbitmq');
const authMiddleware = require('./middlewares/authMiddleware');
const { programarVacaciones, obtenerVacacionesPorEmpleado, actualizarEstado } = require('./controllers/vacacionesController');
const { iniciarCronJob } = require('./jobs/vacacionesCron');
const swaggerDocs = require('./config/swagger');

const app = express();
app.use(cors());
app.use(express.json());

// Configurar Swagger
swaggerDocs(app);

// Endpoints
/**
 * @swagger
 * /vacaciones:
 *   post:
 *     summary: Programa unas nuevas vacaciones
 *     tags: [Vacaciones]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - cedula
 *               - fecha_inicio
 *               - fecha_fin
 *             properties:
 *               cedula:
 *                 type: string
 *                 description: Cédula del empleado
 *               fecha_inicio:
 *                 type: string
 *                 format: date
 *                 description: Fecha de inicio (YYYY-MM-DD)
 *               fecha_fin:
 *                 type: string
 *                 format: date
 *                 description: Fecha de fin (YYYY-MM-DD)
 *     responses:
 *       201:
 *         description: Vacaciones programadas exitosamente
 *       400:
 *         description: Faltan campos, solapamiento o límite excedido
 *       500:
 *         description: Error interno del servidor
 */
app.post('/vacaciones', authMiddleware, programarVacaciones);

/**
 * @swagger
 * /vacaciones/{cedula}:
 *   get:
 *     summary: Obtiene el historial de vacaciones de un empleado
 *     tags: [Vacaciones]
 *     parameters:
 *       - in: path
 *         name: cedula
 *         schema:
 *           type: string
 *         required: true
 *         description: Cédula del empleado
 *     responses:
 *       200:
 *         description: Lista de vacaciones del empleado
 *       500:
 *         description: Error interno del servidor
 */
app.get('/vacaciones/:cedula', authMiddleware, obtenerVacacionesPorEmpleado);

/**
 * @swagger
 * /vacaciones/{id}/estado:
 *   put:
 *     summary: Actualiza el estado de una solicitud de vacaciones
 *     tags: [Vacaciones]
 *     parameters:
 *       - in: path
 *         name: id
 *         schema:
 *           type: integer
 *         required: true
 *         description: ID de la solicitud de vacaciones
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - estado
 *             properties:
 *               estado:
 *                 type: string
 *                 description: Nuevo estado (ej. Cancelada)
 *     responses:
 *       200:
 *         description: Estado actualizado exitosamente
 *       400:
 *         description: Faltan campos
 *       404:
 *         description: Vacaciones no encontradas
 *       500:
 *         description: Error interno del servidor
 */
app.put('/vacaciones/:id/estado', authMiddleware, actualizarEstado);

// Healthcheck
/**
 * @swagger
 * /health:
 *   get:
 *     summary: Verifica el estado de salud del microservicio
 *     tags: [Health]
 *     security: []
 *     responses:
 *       200:
 *         description: Microservicio funcionando correctamente
 */
app.get('/health', (req, res) => {
  res.json({ status: 'UP', service: 'vacaciones-service' });
});

const PORT = process.env.PORT || 80;

const startServer = async () => {
  await initDB();
  await rabbitMQ.connect();
  iniciarCronJob();

  app.listen(PORT, () => {
    console.log(`Servidor de Vacaciones escuchando en el puerto ${PORT}`);
  });
};

startServer();
