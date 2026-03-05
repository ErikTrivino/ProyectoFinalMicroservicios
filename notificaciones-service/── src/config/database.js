const { Sequelize } = require('sequelize');

// La configuración se obtiene de variables de entorno [cite: 90]
const sequelize = new Sequelize(
    process.env.DB_NAME, 
    process.env.DB_USER, 
    process.env.DB_PASSWORD, 
    {
        host: process.env.DB_HOST,
        dialect: 'postgres',
        logging: false // Para mantener la consola limpia
    }
);

module.exports = sequelize;