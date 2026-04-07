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
from requests.exceptions import RequestException
import pika
import json
import jwt
from functools import wraps

load_dotenv()

app = Flask(__name__)

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
        
        # Publicar el evento
        channel.basic_publish(
            exchange='empleados_events',
            routing_key='',
            body=json.dumps(datos_evento),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistente
                type=tipo_evento
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

def _llamar_servicio_departamentos(departamento_id):
    return requests.get(
        f"http://departamentos-service:8081/departamentos/{departamento_id}",
        timeout=3
    )

def validar_departamento(departamento_id, retries=3):

    @breaker
    def llamada_con_breaker():
        return _llamar_servicio_departamentos(departamento_id)

    for intento in range(retries):
        try:
            future = executor.submit(llamada_con_breaker)
            response = future.result()

            if response.status_code == 200:
                return True
            if response.status_code == 404:
                return False

            return False

        except pybreaker.CircuitBreakerError:
            return None

        except RequestException:
            time.sleep(2)

    return None

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

        cur.execute("""
            INSERT INTO empleados (id, cedula, nombre, email, departamento_id, fecha_ingreso)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            emp_id,
            data['cedula'],
            data['nombre'],
            data['email'],
            data['departamentoId'],
            data['fechaIngreso']
        ))

        conn.commit()

        # Publicar evento de empleado creado
        publicar_evento('empleado.creado', {
            'id': emp_id,
            'cedula': data['cedula'],
            'nombre': data['nombre'],
            'email': data['email'],
            'departamentoId': data['departamentoId'],
            'fechaIngreso': data['fechaIngreso']
        })

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
        SELECT id, cedula, nombre, email, departamento_id, fecha_ingreso
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
        "fechaIngreso": row[5].isoformat()
    })

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
            SELECT cedula, nombre, email, departamento_id, fecha_ingreso
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
            'fechaIngreso': row[4].isoformat()
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
            SELECT id, cedula, nombre, email, departamento_id, fecha_ingreso
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
            "fechaIngreso": r[5].isoformat()
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
            fecha_ingreso DATE NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# ======================================================
# MAIN
# ======================================================

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=80, debug=True)