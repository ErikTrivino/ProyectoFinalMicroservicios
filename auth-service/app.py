from flask import Flask, request, jsonify
import os
import json
import time
import datetime
import threading
import jwt
import bcrypt
import pika
import psycopg2
import secrets
import string
from dotenv import load_dotenv
from flasgger import Swagger

"""auth-service/app.py

Servicio de autenticación central del ecosistema de microservicios.
Expone endpoints para iniciar sesión, recuperar/renovar contraseñas,
validar JWT y sincronizar usuarios a partir de eventos de empleados.

El servicio usa PostgreSQL para el almacenamiento de usuarios y RabbitMQ para
publicar y consumir eventos de identidad.
"""

# Cargar variables de entorno desde .env para configurar JWT, BD y RabbitMQ
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
from opentelemetry.propagate import extract, inject

# Aplicación Flask que expone los endpoints de auth-service
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
service_name = os.getenv("OTEL_SERVICE_NAME", "auth-service")
resource = Resource.create({"service.name": service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(zipkin_exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# Métricas Prometheus
metrics = PrometheusMetrics(app)

# Instrumentar Flask
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

JWT_SECRET = os.getenv("JWT_SECRET", "supersecreto")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")





# Tiempo de expiración en minutos para los tokens de acceso
ACCESS_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", 60))
# Tiempo de expiración en minutos para los tokens de recuperación de contraseña
RESET_EXPIRE_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRES_MINUTES", 60))
DB_HOST = os.getenv("DB_HOST", "database-auth")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "auth_db")
DB_USER = os.getenv("DB_USER", "auth_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "auth_pass")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin@message-broker:5672")
ADMIN_USER = os.getenv("AUTH_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("AUTH_ADMIN_PASSWORD", "admin123")
DEFAULT_USER = os.getenv("AUTH_DEFAULT_USER", "user")
DEFAULT_PASSWORD = os.getenv("AUTH_DEFAULT_PASSWORD", "user123")

swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "Servicio de Autenticación JWT",
        "description": "Proveedor central de identidad y emisor de tokens JWT para el ecosistema de microservicios. Emite tokens que deben incluirse en la cabecera 'Authorization: Bearer <token>' en todos los microservicios protegidos.",
        "version": "1.0.0",
        "contact": {
            "name": "Equipo de Seguridad"
        }
    },
    "basePath": "/",
    "schemes": ["http"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using Bearer scheme. Ejemplo: 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'"
        }
    }
})


def get_db():
    """Return a new PostgreSQL connection from configured environment variables."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def init_db():
    """Initialize schema and seed the authentication database.

    Creates the auth_users table if missing and ensures default ADMIN and USER
    accounts exist so other microservices can authenticate against them.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auth_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT,
            role VARCHAR(20) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT FALSE,
            empleado_id VARCHAR(255),
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
    """)
    cur.execute("ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS empleado_id VARCHAR(255);")
    conn.commit()
    cur.close()
    conn.close()
    crear_o_actualizar_usuario(
        ADMIN_USER,
        f"{ADMIN_USER}@empresa.com",
        role='ADMIN',
        active=True,
        password_hash=hash_password(ADMIN_PASSWORD),
        empleado_id='admin'
    )
    crear_o_actualizar_usuario(
        DEFAULT_USER,
        f"{DEFAULT_USER}@empresa.com",
        role='USER',
        active=True,
        password_hash=hash_password(DEFAULT_PASSWORD),
        empleado_id='user'
    )


def log_default_credentials():
    """Print the seeded default authentication credentials for testing."""
    print('***** Credenciales por defecto para pruebas de autenticación *****')
    print(f'ADMIN -> usuario: {ADMIN_USER}, contraseña: {ADMIN_PASSWORD}')
    print(f'USER  -> usuario: {DEFAULT_USER}, contraseña: {DEFAULT_PASSWORD}')
    print('****************************************************************')


def respuesta_exitosa(mensaje, data=None, status=200):
    """Build a success response payload with message and optional data."""
    return jsonify({"success": True, "message": mensaje, "data": data}), status


def respuesta_error(mensaje, status=400):
    """Build an error response payload with a message and HTTP status."""
    return jsonify({"success": False, "message": mensaje, "data": None}), status


def hash_password(password):
    """Hash a plaintext password using bcrypt and return the encoded hash."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password, password_hash):
    """Verify a plaintext password against the stored bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def crear_token(payload, expires_delta):
    """Create a signed JWT with issued-at and expiration claims."""
    now = datetime.datetime.utcnow()
    data = payload.copy()
    data.update({
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp())
    })
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def publicar_evento(exchange, tipo_evento, datos_evento):
    """Publish a durable JSON event to a RabbitMQ fanout exchange."""
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange, exchange_type='fanout', durable=True)
        trace_headers = {}
        inject(trace_headers)
        channel.basic_publish(
            exchange=exchange,
            routing_key='',
            body=json.dumps(datos_evento),
            properties=pika.BasicProperties(
                delivery_mode=2,
                type=tipo_evento,
                headers=trace_headers
            )
        )
        connection.close()
        print(f"Evento publicado {tipo_evento}: {datos_evento}")
    except Exception as e:
        print(f"Error publicando evento {tipo_evento}: {e}")


def obtener_usuario_por_username(username):
    """Return a single user record from auth_users matching the username."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, password_hash, role, active, empleado_id FROM auth_users WHERE username=%s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def obtener_usuario_por_email(email):
    """Return a single user record from auth_users matching the email."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, password_hash, role, active, empleado_id FROM auth_users WHERE email=%s", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def crear_o_actualizar_usuario(username, email, role='USER', active=False, password_hash=None, empleado_id=None):
    """Insert or update a user record in auth_users.

    Keeps username/email uniqueness and updates role, active state, password hash and empleado_id.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM auth_users WHERE username=%s OR email=%s", (username, email))
    existing = cur.fetchone()
    if existing:
        cur.execute(
            "UPDATE auth_users SET role=%s, active=%s, password_hash=%s, empleado_id=%s, updated_at=NOW() WHERE email=%s",
            (role, active, password_hash, empleado_id, email)
        )
    else:
        cur.execute(
            "INSERT INTO auth_users (username, email, role, active, password_hash, empleado_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (username, email, role, active, password_hash, empleado_id)
        )
    conn.commit()
    cur.close()
    conn.close()


def generar_password_temporal(length=12):
    """Generate a secure temporary password for new auto-created users."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def deshabilitar_usuario_por_email(email):
    """Deactivate a user account by email in the auth_users table."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE auth_users SET active=false, updated_at=NOW() WHERE email=%s", (email,))
    conn.commit()
    cur.close()
    conn.close()


def procesar_evento_empleado_creado(event_data):
    """Handle empleado.creado events and create or update the corresponding auth user.

    Generates a password reset token and publishes a usuario.creado event for notifications.
    """
    email = event_data.get('email')
    if not email:
        return
    username = email.lower()
    empleado_id = event_data.get('id')
    provided_password = event_data.get('password')
    if provided_password:
        password_hash = hash_password(provided_password)
        crear_o_actualizar_usuario(username, email, role='USER', active=True, password_hash=password_hash, empleado_id=empleado_id)
        publicar_evento('usuario_events', 'usuario.creado', {
            "email": email,
            "tipo": "usuario.creado",
            "id": empleado_id,
            "empleadoId": empleado_id,
            "hasInitialPassword": True
        })
    else:
        temporary_password = generar_password_temporal()
        password_hash = hash_password(temporary_password)
        crear_o_actualizar_usuario(username, email, role='USER', active=False, password_hash=password_hash, empleado_id=empleado_id)
        reset_token = crear_token(
            {"sub": username, "type": "RESET_PASSWORD"},
            datetime.timedelta(minutes=RESET_EXPIRE_MINUTES)
        )
        publicar_evento('usuario_events', 'usuario.creado', {
            "email": email,
            "token": reset_token,
            "tipo": "usuario.creado",
            "id": empleado_id,
            "empleadoId": empleado_id,
            "needsPasswordReset": True
        })


def procesar_evento_empleado_eliminado(event_data):
    """Handle empleado.eliminado events by deactivating the associated auth user."""
    email = event_data.get('email')
    if not email:
        return
    deshabilitar_usuario_por_email(email)


def start_rabbitmq():
    """Connect to RabbitMQ and consume employee lifecycle events indefinitely."""
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            exchange = 'empleados_events'
            channel.exchange_declare(exchange=exchange, exchange_type='fanout', durable=True)
            q = channel.queue_declare('auth_service_queue', durable=True)
            channel.queue_bind(queue=q.method.queue, exchange=exchange, routing_key='')

            print('Auth-service conectado a RabbitMQ, esperando eventos...')

            def callback(ch, method, properties, body):
                try:
                    parent_context = extract(properties.headers or {}) if properties else None
                    event_data = json.loads(body.decode('utf-8'))
                    event_type = event_data.get('tipo') or (properties.type if properties else None)
                    with tracer.start_as_current_span(f"rabbitmq consume {event_type}", context=parent_context):
                        if event_type == 'empleado.creado':
                            procesar_evento_empleado_creado(event_data)
                        elif event_type == 'empleado.eliminado':
                            procesar_evento_empleado_eliminado(event_data)
                except Exception as err:
                    print(f'Error procesando evento RabbitMQ: {err}')
                finally:
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_consume(queue=q.method.queue, on_message_callback=callback)
            channel.start_consuming()
        except Exception as err:
            print(f'RabbitMQ connection error: {err}')
            time.sleep(5)


@app.route('/auth/login', methods=['POST'])
def login():
    """
    Iniciar sesión y obtener JWT
    ---
    tags:
      - Autenticación
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: Nombre de usuario registrado
              example: admin
            password:
              type: string
              description: Contraseña
              example: admin123
    responses:
      200:
        description: Autenticación exitosa
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Autenticación correcta"
            data:
              type: object
              properties:
                access_token:
                  type: string
                  description: JWT para incluir en Authorization header del resto de servicios
                token_type:
                  type: string
                  example: bearer
                expires_in:
                  type: integer
                  description: Tiempo en segundos hasta expiración (3600 = 60 minutos)
                  example: 3600
                role:
                  type: string
                  enum: [ADMIN, USER]
                  description: Rol del usuario - ADMIN tiene acceso total, USER solo lectura
      400:
        description: |
          Datos incompletos
          - Falta username o password
      401:
        description: |
          Credenciales inválidas
          - Usuario no existe
          - Contraseña incorrecta
          - Usuario no activo
    """
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return respuesta_error("username y password son obligatorios", 400)

    username = data['username'].lower().strip()
    password = data['password']
    user = obtener_usuario_por_username(username)

    if not user:
        return respuesta_error("Credenciales inválidas", 401)

    _, username, email, password_hash, role, active, empleado_id = user
    if not active or not password_hash or not check_password(password, password_hash):
        return respuesta_error("Credenciales inválidas", 401)

    access_token = crear_token(
        {"sub": username, "role": role, "type": "ACCESS", "empleadoId": empleado_id},
        datetime.timedelta(minutes=ACCESS_EXPIRE_MINUTES)
    )

    return respuesta_exitosa("Autenticación correcta", {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_EXPIRE_MINUTES * 60,
        "role": role
    }, 200)


@app.route('/auth/change-password', methods=['POST'])
def change_password():
    data = request.get_json()
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return respuesta_error("Authorization header missing or malformed", 401)
    if not data or 'currentPassword' not in data or 'newPassword' not in data:
        return respuesta_error("currentPassword y newPassword son obligatorios", 400)

    try:
        token = auth_header.split(' ', 1)[1].strip()
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get('type') != 'ACCESS':
            return respuesta_error("Token de acceso invalido", 401)

        username = payload.get('sub')
        user = obtener_usuario_por_username(username)
        if not user:
            return respuesta_error("Usuario no encontrado", 404)

        _, _, _, password_hash, _, active, _ = user
        if not active or not password_hash or not check_password(data['currentPassword'], password_hash):
            return respuesta_error("Contrasena actual invalida", 401)

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE auth_users SET password_hash=%s, active=true, updated_at=NOW() WHERE username=%s",
            (hash_password(data['newPassword']), username)
        )
        conn.commit()
        cur.close()
        conn.close()

        return respuesta_exitosa("Contrasena actualizada correctamente")
    except jwt.ExpiredSignatureError:
        return respuesta_error("Token expirado", 401)
    except jwt.InvalidTokenError:
        return respuesta_error("Token invalido", 401)
    except Exception as e:
        return respuesta_error(str(e), 500)


@app.route('/auth/recover-password', methods=['POST'])
def recover_password():
    """
    Solicitar recuperación de contraseña
    ---
    tags:
      - Recuperación
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              description: Email del usuario
              example: admin@empresa.com
    responses:
      200:
        description: Solicitud procesada (no revela si el email existe)
      400:
        description: Email no proporcionado
    """
    data = request.get_json()
    if not data or 'email' not in data:
        return respuesta_error("email es obligatorio", 400)

    email = data['email']
    user = obtener_usuario_por_email(email)
    if user:
        username = user[1]
        empleado_id = user[6]
        reset_token = crear_token(
            {"sub": username, "type": "RESET_PASSWORD"},
            datetime.timedelta(minutes=RESET_EXPIRE_MINUTES)
        )
        publicar_evento('usuario_events', 'usuario.recuperacion', {
            "email": email,
            "token": reset_token,
            "tipo": "usuario.recuperacion",
            "id": empleado_id,
            "empleadoId": empleado_id
        })

    return respuesta_exitosa("Si el correo existe, se ha enviado un enlace de recuperación.")


@app.route('/auth/reset-password', methods=['POST'])
def reset_password():
    """
    Restablecer contraseña con token
    ---
    tags:
      - Recuperación
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - token
            - newPassword
          properties:
            token:
              type: string
              description: Token de recuperación recibido en notificación
            newPassword:
              type: string
              description: Nueva contraseña
              example: nuevaPassword123
    responses:
      200:
        description: Contraseña restablecida exitosamente
      400:
        description: Datos incompletos
      401:
        description: Token expirado o inválido
      404:
        description: Usuario no encontrado
    """
    data = request.get_json()
    if not data or 'token' not in data or 'newPassword' not in data:
        return respuesta_error("token y newPassword son obligatorios", 400)

    token = data['token']
    new_password = data['newPassword']

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get('type') != 'RESET_PASSWORD':
            return respuesta_error("Token de recuperación inválido", 401)

        username = payload.get('sub')
        user = obtener_usuario_por_username(username)
        if not user:
            return respuesta_error("Usuario no encontrado", 404)

        password_hash = hash_password(new_password)
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE auth_users SET password_hash=%s, active=true, updated_at=NOW() WHERE username=%s",
            (password_hash, username)
        )
        conn.commit()
        cur.close()
        conn.close()

        return respuesta_exitosa("Contraseña restablecida correctamente")
    except jwt.ExpiredSignatureError:
        return respuesta_error("Token de recuperación expirado", 401)
    except jwt.InvalidTokenError:
        return respuesta_error("Token de recuperación inválido", 401)
    except Exception as e:
        return respuesta_error(str(e), 500)


@app.route('/auth/validate', methods=['POST'])
def validate_token():
    """
    Validar un JWT
    ---
    tags:
      - Utilidades
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - token
          properties:
            token:
              type: string
              description: Token JWT a validar
    responses:
      200:
        description: Token válido
      400:
        description: Token no proporcionado
      401:
        description: Token inválido o expirado
    """
    data = request.get_json()
    token = data.get('token') if data else None
    if not token:
        return respuesta_error("token requerido", 400)

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return respuesta_exitosa("Token válido", {"payload": payload}, 200)
    except jwt.ExpiredSignatureError:
        return respuesta_error("Token expirado", 401)
    except jwt.InvalidTokenError:
        return respuesta_error("Token inválido", 401)


@app.route('/health', methods=['GET'])
def health():
    """
    Health check del servicio
    ---
    tags:
      - Utilidades
    responses:
      200:
        description: Servicio operacional
    """
    return respuesta_exitosa("auth-service OK")


if __name__ == '__main__':
    init_db()
    log_default_credentials()
    threading.Thread(target=start_rabbitmq, daemon=True).start()
    app.run(host='0.0.0.0', port=80)
