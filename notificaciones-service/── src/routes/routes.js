const express = require('express');
const router = express.Router();
const Notification = require('./models/Notification');

// GET /notificaciones: Lista todo el historial [cite: 77]
router.get('/', async (req, res) => {
    const data = await Notification.find();
    res.json(data);
});

// GET /notificaciones/{empleadoId}: Filtra por empleado [cite: 77]
router.get('/:empleadoId', async (req, res) => {
    const data = await Notification.find({ empleadoId: req.params.empleadoId });
    res.json(data);
});

module.exports = router;