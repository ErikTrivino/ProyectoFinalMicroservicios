const { Pool } = require('pg');

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'vacaciones_db',
  user: process.env.DB_USER || 'vacaciones_user',
  password: process.env.DB_PASSWORD || 'vacaciones_pass',
});

const initDB = async () => {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS vacaciones (
        id SERIAL PRIMARY KEY,
        cedula VARCHAR(20) NOT NULL,
        fecha_inicio DATE NOT NULL,
        fecha_fin DATE NOT NULL,
        dias_solicitados INTEGER NOT NULL,
        estado VARCHAR(50) NOT NULL DEFAULT 'Programada',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);
    console.log('Tabla vacaciones verificada/creada con éxito.');
  } catch (error) {
    console.error('Error inicializando la base de datos:', error);
  }
};

module.exports = {
  pool,
  initDB
};
