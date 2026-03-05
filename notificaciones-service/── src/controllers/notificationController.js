const Notification = require('../models/Notification');

exports.getAll = async (req, res) => {
    try {
        const list = await Notification.find();
        res.status(200).json(list);
    } catch (err) {
        res.status(500).json({ error: "Error al obtener notificaciones" });
    }
};

exports.getByEmpleado = async (req, res) => {
    try {
        // Filtra por el ID del empleado recibido en la URL [cite: 77, 133]
        const list = await Notification.find({ empleadoId: req.params.empleadoId });
        res.status(200).json(list);
    } catch (err) {
        res.status(500).json({ error: "Error al obtener historial del empleado" });
    }
};