const { pool } = require('../config/db');
const rabbitMQ = require('../config/rabbitmq');
const axios = require('axios');

const EMPLEADOS_SERVICE_URL = process.env.EMPLEADOS_SERVICE_URL || 'http://empleados-service:80';

const programarVacaciones = async (req, res) => {
  const { cedula, fecha_inicio, fecha_fin } = req.body;

  if (!cedula || !fecha_inicio || !fecha_fin) {
    return res.status(400).json({ message: 'Faltan campos requeridos (cedula, fecha_inicio, fecha_fin)' });
  }

  const authHeader = req.headers.authorization;
  if (!authHeader) {
    return res.status(401).json({ message: 'Token de autorización requerido' });
  }

  let empleadoData;
  try {
    const response = await axios.get(`${EMPLEADOS_SERVICE_URL}/empleados/cedula/${cedula}`, {
      headers: { Authorization: authHeader }
    });
    empleadoData = response.data.data;
    if (empleadoData.estado !== 'ACTIVO') {
      return res.status(400).json({ message: `No se pueden programar vacaciones para un empleado cuyo estado es: ${empleadoData.estado}` });
    }
  } catch (error) {
    if (error.response && error.response.status === 404) {
      return res.status(404).json({ message: 'El empleado con esta cédula no existe' });
    }
    return res.status(500).json({ message: 'Error validando empleado', details: error.message });
  }

  try {
    // Calcular días solicitados
    const inicio = new Date(fecha_inicio);
    const fin = new Date(fecha_fin);
    const diffTime = Math.abs(fin - inicio);
    const dias_solicitados = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;

    if (dias_solicitados <= 0) {
      return res.status(400).json({ message: 'La fecha de fin debe ser posterior o igual a la fecha de inicio.' });
    }

    // Validar solapamiento
    const overlappingQuery = `
      SELECT id FROM vacaciones
      WHERE cedula = $1
      AND estado != 'Cancelada'
      AND (
        (fecha_inicio <= $2 AND fecha_fin >= $2) OR
        (fecha_inicio <= $3 AND fecha_fin >= $3) OR
        (fecha_inicio >= $2 AND fecha_fin <= $3)
      )
    `;
    const result = await pool.query(overlappingQuery, [cedula, fecha_inicio, fecha_fin]);

    if (result.rows.length > 0) {
      return res.status(400).json({ message: 'El empleado ya tiene vacaciones programadas que se solapan con este período.' });
    }

    // Validar días disponibles (Asumiendo un máximo de 15 días por año)
    const MAX_DIAS_ANUALES = 15;
    const usedDaysQuery = `
      SELECT SUM(dias_solicitados) as used_days 
      FROM vacaciones 
      WHERE cedula = $1 AND estado != 'Cancelada'
    `;
    const usedDaysResult = await pool.query(usedDaysQuery, [cedula]);
    const usedDays = parseInt(usedDaysResult.rows[0].used_days || 0);

    if (usedDays + dias_solicitados > MAX_DIAS_ANUALES) {
      return res.status(400).json({ 
        message: `No hay suficientes días disponibles. Solicitados: ${dias_solicitados}, Ya utilizados: ${usedDays}, Límite: ${MAX_DIAS_ANUALES}` 
      });
    }

    // Insertar en BD
    const insertQuery = `
      INSERT INTO vacaciones (cedula, empleado_id, email, fecha_inicio, fecha_fin, dias_solicitados, estado)
      VALUES ($1, $2, $3, $4, $5, $6, 'Programada')
      RETURNING *;
    `;
    const insertResult = await pool.query(insertQuery, [cedula, empleadoData.id, empleadoData.email, fecha_inicio, fecha_fin, dias_solicitados]);
    const nuevaVacacion = insertResult.rows[0];

    // Publicar evento (notificaciones-service escuchará esto)
    rabbitMQ.publishEvent('vacaciones.programadas', {
      tipo: 'vacaciones.programadas',
      cedula,
      empleado_id: empleadoData.id,
      email: empleadoData.email,
      fecha_inicio,
      fecha_fin,
      dias_solicitados,
      vacacion_id: nuevaVacacion.id,
      timestamp: new Date().toISOString()
    });
    
    // Log para simular el evento
    console.log(`[LOG] Evento 'vacaciones.programadas' enviado para cedula: ${cedula}`);

    res.status(201).json({
      message: 'Vacaciones programadas exitosamente',
      data: nuevaVacacion
    });

  } catch (error) {
    console.error('Error al programar vacaciones:', error);
    res.status(500).json({ message: 'Error interno del servidor' });
  }
};

const obtenerVacacionesPorEmpleado = async (req, res) => {
  const { cedula } = req.params;
  try {
    const result = await pool.query('SELECT * FROM vacaciones WHERE cedula = $1 ORDER BY fecha_inicio DESC', [cedula]);
    res.json(result.rows);
  } catch (error) {
    console.error('Error obteniendo vacaciones:', error);
    res.status(500).json({ message: 'Error interno del servidor' });
  }
};

const actualizarEstado = async (req, res) => {
  const { cedula } = req.params;
  const { estado } = req.body; // ej. "Cancelada"

  if (!estado) {
    return res.status(400).json({ message: 'Estado es requerido' });
  }

  try {
    // Actualiza la solicitud de vacaciones más reciente que esté activa (Programada o En Curso) para esa cédula
    const result = await pool.query(
      `UPDATE vacaciones SET estado = $1
       WHERE id = (
         SELECT id FROM vacaciones
         WHERE cedula = $2 AND estado IN ('Programada', 'En Curso')
         ORDER BY fecha_inicio DESC
         LIMIT 1
       )
       RETURNING *`,
      [estado, cedula]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ message: 'No se encontraron vacaciones activas (Programada o En Curso) para esta cédula' });
    }
    res.json({ message: 'Estado actualizado', data: result.rows[0] });
  } catch (error) {
    console.error('Error actualizando estado:', error);
    res.status(500).json({ message: 'Error interno del servidor' });
  }
};

module.exports = {
  programarVacaciones,
  obtenerVacacionesPorEmpleado,
  actualizarEstado
};
