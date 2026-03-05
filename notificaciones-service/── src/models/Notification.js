const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');

const Notification = sequelize.define('Notification', {
    id: {
        type: DataTypes.UUID,
        defaultValue: DataTypes.UUIDV4,
        primaryKey: true
    },
    tipo: {
        type: DataTypes.ENUM('BIENVENIDA', 'DESVINCULACION'),
        allowNull: false
    },
    destinatario: {
        type: DataTypes.STRING, // Email
        allowNull: false
    },
    mensaje: {
        type: DataTypes.TEXT,
        allowNull: false
    },
    fechaEnvio: {
        type: DataTypes.DATE,
        defaultValue: DataTypes.NOW
    },
    empleadoId: {
        type: DataTypes.STRING, // ID que viene del evento [cite: 86]
        allowNull: false
    }
});

module.exports = Notification;