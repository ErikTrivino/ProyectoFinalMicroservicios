const cron = require('node-cron');
const { pool } = require('../config/db');
const rabbitMQ = require('../config/rabbitmq');

const iniciarCronJob = () => {
  // Ejecutar todos los días a las 00:01
  cron.schedule('1 0 * * *', async () => {
    console.log('--- Ejecutando Cron Job de revisión de vacaciones ---');
    try {
      const hoy = new Date().toISOString().split('T')[0]; // YYYY-MM-DD

      // 1. Desactivar cuentas para vacaciones que inician HOY
      const inicianHoyQuery = `
        SELECT id, cedula, empleado_id, email FROM vacaciones 
        WHERE fecha_inicio <= $1 AND estado = 'Programada'
      `;
      const inicianHoyResult = await pool.query(inicianHoyQuery, [hoy]);
      
      for (const vacacion of inicianHoyResult.rows) {
        // Actualizar estado interno a 'En Curso'
        await pool.query("UPDATE vacaciones SET estado = 'En Curso' WHERE id = $1", [vacacion.id]);
        
        // Publicar evento para desactivar empleado
        rabbitMQ.publishEvent('empleado.estado.cambiado', {
          tipo: 'empleado.estado.cambiado',
          cedula: vacacion.cedula,
          empleado_id: vacacion.empleado_id,
          email: vacacion.email,
          nuevoEstado: 'EN_VACACIONES',
          motivo: 'Inicio de vacaciones'
        });
        console.log(`[LOG] Evento 'empleado.estado.cambiado' (Desactivación - EN_VACACIONES) enviado para cedula: ${vacacion.cedula}`);
      }

      // 2. Reactivar cuentas para vacaciones que finalizan ANTES DE HOY o igual a ayer
      const terminaronQuery = `
        SELECT id, cedula, empleado_id, email FROM vacaciones 
        WHERE fecha_fin < $1 AND estado = 'En Curso'
      `;
      const terminaronResult = await pool.query(terminaronQuery, [hoy]);

      for (const vacacion of terminaronResult.rows) {
        // Actualizar estado interno a 'Finalizada'
        await pool.query("UPDATE vacaciones SET estado = 'Finalizada' WHERE id = $1", [vacacion.id]);
        
        // Publicar evento para reactivar empleado
        rabbitMQ.publishEvent('empleado.estado.cambiado', {
          tipo: 'empleado.estado.cambiado',
          cedula: vacacion.cedula,
          empleado_id: vacacion.empleado_id,
          email: vacacion.email,
          nuevoEstado: 'ACTIVO',
          motivo: 'Fin de vacaciones'
        });
        console.log(`[LOG] Evento 'empleado.estado.cambiado' (Reactivación - ACTIVO) enviado para cedula: ${vacacion.cedula}`);
      }

    } catch (error) {
      console.error('Error durante la ejecución del Cron Job de vacaciones:', error);
    }
  });
  console.log('Cron Job de revisión de vacaciones programado (00:01 diariamente).');
};

module.exports = { iniciarCronJob };
