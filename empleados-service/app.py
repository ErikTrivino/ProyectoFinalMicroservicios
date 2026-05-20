from flask import Flask, request, jsonify, g
import psycopg2
import uuid
import os
import time
from dotenv import load_dotenv
from flasgger import Swagger
import requests
import pybreaker
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from requests.exceptions import RequestException
import pika
import json
import jwt
from functools import wraps

load_dotenv()

import logging
from pythonjsonlogger import jsonlogger
from prometheus_flask_exporter import PrometheusMetrics
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import inject

app = Flask(__name__)

# Logs estructurados
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# OpenTelemetry y Zipkin
zipkin_exporter = ZipkinExporter(endpoint="http://zipkin:9411/api/v2/spans")
service_name = os.getenv("OTEL_SERVICE_NAME", "empleados-service")
resource = Resource.create({"service.name": service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(zipkin_exporter))
trace.set_tracer_provider(provider)

# Métricas Prometheus
metrics = PrometheusMetrics(app)

# Instrumentar Flask
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# ======================================================
# CONFIGURACIÓN SWAGGER
# ======================================================

JWT_SECRET = os.getenv("JWT_SECRET", "supersecreto")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "API Empleados",
        "description": "Servicio de gestión de empleados con resiliencia (Circuit Breaker + Bulkhead)",
        "version": "1.0.0"
    },
    "basePath": "/",
    "schemes": ["http"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: 'Authorization: Bearer {token}'"
        }
    },
    "security": [{"Bearer": []}]
})

# ======================================================
# CONFIGURACIÓN RESILIENCIA
# ======================================================

breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=30
)

executor = ThreadPoolExecutor(max_workers=5)

# ======================================================
# PUBLICACIÓN DE EVENTOS (RabbitMQ)
# ======================================================

def publicar_evento(tipo_evento, datos_evento):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "message-broker"),
            port=int(os.getenv("RABBITMQ_PORT", 5672)),
            credentials=pika.PlainCredentials(
                os.getenv("RABBITMQ_USER", "admin"),
                os.getenv("RABBITMQ_PASS", "admin")
            )
        ))
        channel = connection.channel()
        
        # Declarar el exchange
        channel.exchange_declare(exchange='empleados_events', exchange_type='fanout', durable=True)
        
        trace_headers = {}
        inject(trace_headers)

        # Publicar el evento con contexto W3C para consumidores asincronos.
        channel.basic_publish(
            exchange='empleados_events',
            routing_key='',
            body=json.dumps(datos_evento),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistente
                type=tipo_evento,
                headers=trace_headers
            )
        )
        
        connection.close()
        print(f"Evento publicado: {tipo_evento}")
        
    except Exception as e:
        print(f"Error publicando evento: {str(e)}")

# ======================================================
# CONEXIÓN POSTGRESQL
# ======================================================

def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# ======================================================
# CONEXION RABBITMQ (Reto 3)
# ======================================================

def get_rabbitmq_connection():
    """Crea una conexion a RabbitMQ con reintentos."""
    rabbitmq_host = os.getenv("RABBITMQ_HOST", "message-broker")
    rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
    rabbitmq_user = os.getenv("RABBITMQ_USER", "admin")
    rabbitmq_pass = os.getenv("RABBITMQ_PASS", "admin")

    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
    parameters = pika.ConnectionParameters(
        host=rabbitmq_host,
        port=rabbitmq_port,
        credentials=credentials,
        connection_attempts=3,
        retry_delay=2
    )
    return pika.BlockingConnection(parameters)


# ======================================================
# RESPUESTAS ESTÁNDAR
# ======================================================

def respuesta_exitosa(mensaje, data=None, status=200):
    return jsonify({"success": True, "message": mensaje, "data": data}), status

def respuesta_error(mensaje, status=400):
    return jsonify({"success": False, "message": mensaje, "data": None}), status

# ======================================================
# AUTENTICACIÓN Y RBAC
# ======================================================

def obtener_token_autorizacion():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    return auth_header.split(' ', 1)[1].strip()


def validar_token(token):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return payload


def requerir_rol(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = obtener_token_autorizacion()
            if not token:
                return respuesta_error('Authorization header missing or malformed', 401)
            try:
                payload = validar_token(token)
            except jwt.ExpiredSignatureError:
                return respuesta_error('Token expirado', 401)
            except jwt.InvalidTokenError:
                return respuesta_error('Token inválido', 401)

            if payload.get('role') not in roles:
                return respuesta_error('Permiso denegado', 403)

            g.user = payload.get('sub')
            g.role = payload.get('role')
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ======================================================
# VALIDACIÓN DE DEPARTAMENTO (Resiliente)
# ======================================================

DEPARTAMENTOS_SERVICE_URL = os.getenv("DEPARTAMENTOS_SERVICE_URL", "http://departamentos-service:8081")

def _llamar_servicio_departamentos(departamento_id, auth_header):
    return requests.get(
        f"{DEPARTAMENTOS_SERVICE_URL}/departamentos/{departamento_id}",
        headers={"Authorization": auth_header} if auth_header else {},
        timeout=3
    )

def validar_departamento(departamento_id, retries=3):
    auth_header = request.headers.get("Authorization")

    @breaker
    def llamada_con_breaker():
        return _llamar_servicio_departamentos(departamento_id, auth_header)

    for intento in range(retries):
        try:
            ctx = copy_context()
            future = executor.submit(ctx.run, llamada_con_breaker)
            response = future.result()

            if response.status_code == 200:
                return True
            if response.status_code == 404:
                return False
            if response.status_code == 401:
                return "unauthorized"

            return False

        except pybreaker.CircuitBreakerError:
            return None

        except RequestException:
            time.sleep(2)

    return None

# ======================================================
# GET /health
# ======================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


# ======================================================
# POST /empleados
# ======================================================

@app.route('/empleados', methods=['POST'])
@requerir_rol('ADMIN')
def registrar_empleado():
    """
    Registrar un nuevo empleado
    ---
    tags:
      - Empleados
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - cedula
            - nombre
            - email
            - departamentoId
            - fechaIngreso
          properties:
            cedula:
              type: string
              example: "123456789"
            nombre:
              type: string
              example: "Juan Pérez"
            email:
              type: string
              example: "juan@email.com"
            departamentoId:
              type: string
              example: "1"
            fechaIngreso:
              type: string
              format: date
              example: "2024-01-01"
            estado:
              type: string
              enum: ["ACTIVO", "EN_VACACIONES", "RETIRADO"]
              default: "ACTIVO"
              example: "ACTIVO"
            password:
              type: string
              description: "Contraseña inicial opcional para el usuario asociado"
              example: "Pass1234"
    responses:
      201:
        description: Empleado registrado correctamente
      400:
        description: Datos inválidos
      409:
        description: Cédula ya existe
      503:
        description: Servicio de departamentos no disponible
    """

    data = request.get_json()

    if not data:
        return respuesta_error("El cuerpo es obligatorio")

    campos = ['cedula', 'nombre', 'email', 'departamentoId', 'fechaIngreso']
    if not all(c in data for c in campos):
        return respuesta_error("Datos incompletos")

    validacion = validar_departamento(data['departamentoId'])

    if validacion == "unauthorized":
        return respuesta_error("Token inválido o faltante para el servicio de departamentos", 401)

    if validacion is False:
        return respuesta_error("El departamento no existe", 400)

    if validacion is None:
        return respuesta_error("Servicio de departamentos no disponible", 503)

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("SELECT 1 FROM empleados WHERE cedula=%s", (data['cedula'],))
        if cur.fetchone():
            return respuesta_error("La cédula ya existe", 409)

        emp_id = str(uuid.uuid4())

        estado = data.get('estado', 'ACTIVO')
        if estado not in ['ACTIVO', 'EN_VACACIONES', 'RETIRADO']:
            return respuesta_error("Estado inválido. Valores permitidos: ACTIVO, EN_VACACIONES, RETIRADO", 400)

        cur.execute("""
            INSERT INTO empleados (id, cedula, nombre, email, departamento_id, fecha_ingreso, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            emp_id,
            data['cedula'],
            data['nombre'],
            data['email'],
            data['departamentoId'],
            data['fechaIngreso'],
            estado
        ))

        conn.commit()

        # Publicar evento de empleado creado
        event_data = {
            'id': emp_id,
            'cedula': data['cedula'],
            'nombre': data['nombre'],
            'email': data['email'],
            'departamentoId': data['departamentoId'],
            'fechaIngreso': data['fechaIngreso'],
            'estado': estado
        }
        if 'password' in data and data['password']:
            event_data['password'] = data['password']

        publicar_evento('empleado.creado', event_data)

        return respuesta_exitosa("Empleado registrado", {
            "id": emp_id,
            **data
        }, 201)

    except Exception as e:
        conn.rollback()
        return respuesta_error(str(e), 500)

    finally:
        cur.close()
        conn.close()


# ======================================================
# GET /empleados/{id}
# ======================================================

@app.route('/empleados/<id>', methods=['GET'])
@requerir_rol('USER', 'ADMIN')
def obtener_empleado(id):
    """
    Obtener empleado por ID
    ---
    tags:
      - Empleados
    parameters:
      - name: id
        in: path
        type: string
        required: true
        description: ID del empleado
    responses:
      200:
        description: Empleado encontrado
      404:
        description: Empleado no existe
    """

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, cedula, nombre, email, departamento_id, fecha_ingreso, estado
        FROM empleados WHERE id=%s
    """, (id,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return respuesta_error("Empleado no existe", 404)

    return respuesta_exitosa("Empleado encontrado", {
        "id": row[0],
        "cedula": row[1],
        "nombre": row[2],
        "email": row[3],
        "departamentoId": row[4],
        "fechaIngreso": row[5].isoformat(),
        "estado": row[6]
    })


# ======================================================
# PUT /empleados/{id}
# ======================================================

@app.route('/empleados/<id>', methods=['PUT'])
@requerir_rol('ADMIN')
def actualizar_empleado(id):
    data = request.get_json()
    if not data:
        return respuesta_error("El cuerpo es obligatorio")

    campos_permitidos = {
        'cedula': 'cedula',
        'nombre': 'nombre',
        'email': 'email',
        'departamentoId': 'departamento_id',
        'fechaIngreso': 'fecha_ingreso',
        'estado': 'estado'
    }
    cambios = {campo: data[campo] for campo in campos_permitidos if campo in data}
    if not cambios:
        return respuesta_error("No hay campos validos para actualizar")

    if 'estado' in cambios and cambios['estado'] not in ['ACTIVO', 'EN_VACACIONES', 'RETIRADO']:
        return respuesta_error("Estado invalido. Valores permitidos: ACTIVO, EN_VACACIONES, RETIRADO", 400)

    if 'departamentoId' in cambios:
        validacion = validar_departamento(cambios['departamentoId'])
        if validacion == "unauthorized":
            return respuesta_error("Token invalido o faltante para el servicio de departamentos", 401)
        if validacion is False:
            return respuesta_error("El departamento no existe", 400)
        if validacion is None:
            return respuesta_error("Servicio de departamentos no disponible", 503)

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("SELECT 1 FROM empleados WHERE id=%s", (id,))
        if not cur.fetchone():
            return respuesta_error("Empleado no existe", 404)

        assignments = []
        values = []
        for campo_api, valor in cambios.items():
            assignments.append(f"{campos_permitidos[campo_api]}=%s")
            values.append(valor)
        values.append(id)

        cur.execute(f"UPDATE empleados SET {', '.join(assignments)} WHERE id=%s", values)
        conn.commit()

        cur.execute("""
            SELECT id, cedula, nombre, email, departamento_id, fecha_ingreso, estado
            FROM empleados WHERE id=%s
        """, (id,))
        row = cur.fetchone()

        return respuesta_exitosa("Empleado actualizado", {
            "id": row[0],
            "cedula": row[1],
            "nombre": row[2],
            "email": row[3],
            "departamentoId": row[4],
            "fechaIngreso": row[5].isoformat(),
            "estado": row[6]
        })
    except Exception as e:
        conn.rollback()
        return respuesta_error(str(e), 500)
    finally:
        cur.close()
        conn.close()

# ======================================================
# DELETE /empleados/{id}
# ======================================================

@app.route('/empleados/<id>', methods=['DELETE'])
@requerir_rol('ADMIN')
def eliminar_empleado(id):
    """
    Eliminar empleado por ID
    ---
    tags:
      - Empleados
    parameters:
      - name: id
        in: path
        type: string
        required: true
        description: ID del empleado
    responses:
      200:
        description: Empleado eliminado correctamente
      404:
        description: Empleado no existe
      500:
        description: Error interno del servidor
    """

    conn = get_db()
    cur = conn.cursor()

    try:
        # Verificar que el empleado existe y obtener sus datos
        cur.execute("""
            SELECT cedula, nombre, email, departamento_id, fecha_ingreso, estado
            FROM empleados WHERE id=%s
        """, (id,))
        
        row = cur.fetchone()
        if not row:
            return respuesta_error("Empleado no existe", 404)
        
        # Guardar datos para el evento
        empleado_data = {
            'id': id,
            'cedula': row[0],
            'nombre': row[1],
            'email': row[2],
            'departamentoId': row[3],
            'fechaIngreso': row[4].isoformat(),
            'estado': row[5]
        }
        
        # Eliminar el empleado
        cur.execute("DELETE FROM empleados WHERE id=%s", (id,))
        conn.commit()
        
        # Publicar evento de empleado eliminado
        publicar_evento('empleado.eliminado', empleado_data)
        
        return respuesta_exitosa("Empleado eliminado correctamente")
        
    except Exception as e:
        conn.rollback()
        return respuesta_error(str(e), 500)
    
    finally:
        cur.close()
        conn.close()

# ======================================================
# POST /empleados/{id}/offboard
# ======================================================

@app.route('/empleados/<id>/offboard', methods=['POST'])
@requerir_rol('ADMIN')
def offboarding_empleado(id):
    """
    Offboarding de un empleado
    ---
    tags:
      - Empleados
    parameters:
      - name: id
        in: path
        type: string
        required: true
        description: ID del empleado
    responses:
      200:
        description: Empleado retirado correctamente
      400:
        description: El empleado ya se encuentra retirado
      404:
        description: Empleado no existe
      500:
        description: Error interno del servidor
    """

    conn = get_db()
    cur = conn.cursor()

    try:
        # Verificar que el empleado existe y obtener sus datos
        cur.execute("""
            SELECT cedula, nombre, email, departamento_id, fecha_ingreso, estado
            FROM empleados WHERE id=%s
        """, (id,))
        
        row = cur.fetchone()
        if not row:
            return respuesta_error("Empleado no existe", 404)
            
        estado_actual = row[5]
        if estado_actual == 'RETIRADO':
            return respuesta_error("El empleado ya se encuentra retirado", 400)
        
        # Guardar datos para el evento
        empleado_data = {
            'id': id,
            'cedula': row[0],
            'nombre': row[1],
            'email': row[2],
            'departamentoId': row[3],
            'fechaIngreso': row[4].isoformat(),
            'estado': 'RETIRADO'
        }
        
        # Actualizar estado a RETIRADO
        cur.execute("UPDATE empleados SET estado='RETIRADO' WHERE id=%s", (id,))
        
        # Registro de auditoría de la fecha y hora de la desactivación
        cur.execute("""
            INSERT INTO auditoria_offboarding (empleado_id, detalles)
            VALUES (%s, %s)
        """, (id, "Offboarding completado: credenciales y accesos desactivados permanentemente"))
        
        conn.commit()
        
        # Publicar evento de empleado eliminado para que auth-service desactive las credenciales permanentemente
        publicar_evento('empleado.eliminado', empleado_data)
        
        return respuesta_exitosa("Empleado retirado y accesos desactivados permanentemente")
        
    except Exception as e:
        conn.rollback()
        return respuesta_error(str(e), 500)
    
    finally:
        cur.close()
        conn.close()

# ======================================================
# GET /empleados (Paginado)
# ======================================================

@app.route('/empleados', methods=['GET'])
@requerir_rol('USER', 'ADMIN')
def listar_empleados():
    """
    Listar empleados con paginación
    ---
    tags:
      - Empleados
    parameters:
      - name: page
        in: query
        type: integer
        required: false
        default: 1
      - name: size
        in: query
        type: integer
        required: false
        default: 10
    responses:
      200:
        description: Lista paginada de empleados
      400:
        description: Parámetros inválidos
    """

    page = request.args.get('page', default=1, type=int)
    size = request.args.get('size', default=10, type=int)

    if page < 1 or size < 1:
        return respuesta_error("page y size deben ser mayores que 0")

    offset = (page - 1) * size

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("SELECT COUNT(*) FROM empleados")
        total_items = cur.fetchone()[0]

        cur.execute("""
            SELECT id, cedula, nombre, email, departamento_id, fecha_ingreso, estado
            FROM empleados
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (size, offset))

        empleados = [{
            "id": r[0],
            "cedula": r[1],
            "nombre": r[2],
            "email": r[3],
            "departamentoId": r[4],
            "fechaIngreso": r[5].isoformat(),
            "estado": r[6]
        } for r in cur.fetchall()]

        total_pages = (total_items + size - 1) // size

        return respuesta_exitosa(
            "Lista de empleados",
            {
                "items": empleados,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total_items": total_items,
                    "total_pages": total_pages
                }
            }
        )

    except Exception as e:
        return respuesta_error(str(e), 500)

    finally:
        cur.close()
        conn.close()

# ======================================================
# INIT DB
# ======================================================

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id VARCHAR(36) PRIMARY KEY,
            cedula VARCHAR(20) UNIQUE NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL,
            departamento_id VARCHAR(20) NOT NULL,
            fecha_ingreso DATE NOT NULL,
            estado VARCHAR(20) DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'EN_VACACIONES', 'RETIRADO'))
        );
    """)
    cur.execute("ALTER TABLE empleados ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'ACTIVO';")
    cur.execute("UPDATE empleados SET estado='ACTIVO' WHERE estado IS NULL;")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auditoria_offboarding (
            id SERIAL PRIMARY KEY,
            empleado_id VARCHAR(36) NOT NULL,
            fecha_desactivacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            detalles TEXT
        );
    """)
    
    conn.commit()
    cur.close()
    conn.close()

# ======================================================
# CONSUMIDOR DE EVENTOS (RabbitMQ)
# ======================================================

def iniciar_consumidor():
    def callback(ch, method, properties, body):
        try:
            datos = json.loads(body)
            tipo = datos.get('tipo')
            if tipo == 'empleado.estado.cambiado':
                emp_id = datos.get('empleado_id')
                nuevo_estado = datos.get('nuevoEstado')
                
                conn = get_db()
                cur = conn.cursor()
                cur.execute("UPDATE empleados SET estado=%s WHERE id=%s", (nuevo_estado, emp_id))
                conn.commit()
                cur.close()
                conn.close()
                print(f"[CONSUMER] Estado de empleado {emp_id} actualizado a {nuevo_estado}")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"[CONSUMER] Error procesando mensaje: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Declarar el exchange (debe coincidir)
        channel.exchange_declare(exchange='empleados_events', exchange_type='fanout', durable=True)
        
        # Cola exclusiva para este consumidor
        result = channel.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue
        
        channel.queue_bind(exchange='empleados_events', queue=queue_name)
        
        channel.basic_consume(queue=queue_name, on_message_callback=callback)
        print("[CONSUMER] Escuchando eventos en empleados_events...")
        channel.start_consuming()
    except Exception as e:
        print(f"[CONSUMER] Error en el consumidor: {str(e)}")

# ======================================================
# MAIN
# ======================================================

if __name__ == '__main__':
    init_db()
    
    # Iniciar consumidor en un hilo separado
    import threading
    t = threading.Thread(target=iniciar_consumidor)
    t.daemon = True
    t.start()
    
    app.run(host='0.0.0.0', port=80)
