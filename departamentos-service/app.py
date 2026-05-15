from flask import Flask, request, jsonify, g
import psycopg2
import os
import random
import time
from dotenv import load_dotenv
from flasgger import Swagger, swag_from
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
service_name = os.getenv("OTEL_SERVICE_NAME", "departamentos-service")
resource = Resource.create({"service.name": service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(zipkin_exporter))
trace.set_tracer_provider(provider)

# Métricas Prometheus
metrics = PrometheusMetrics(app)

# Instrumentar Flask
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

JWT_SECRET = os.getenv("JWT_SECRET", "supersecreto")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "API Departamentos",
        "description": "Servicio de gestión de departamentos",
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

# =========================
# Conexión a PostgreSQL
# =========================
def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# =========================
# Respuestas estándar
# =========================
def respuesta_exitosa(mensaje, data=None, status=200):
    return jsonify({"success": True, "message": mensaje, "data": data}), status

def respuesta_error(mensaje, status=400):
    return jsonify({"success": False, "message": mensaje, "data": None}), status

# =========================
# AUTENTICACIÓN Y RBAC
# =========================

def obtener_token_autorizacion():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    return auth_header.split(' ', 1)[1].strip()


def validar_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


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

# =========================
# POST /departamentos
# =========================
@app.route('/departamentos', methods=['POST'])
@swag_from({
    'tags': ['Departamentos'],
    'description': 'Registra un nuevo departamento',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['id', 'nombre', 'descripcion'],
                'properties': {
                    'id': {'type': 'string', 'example': 'IT'},
                    'nombre': {'type': 'string', 'example': 'Tecnología'},
                    'descripcion': {'type': 'string', 'example': 'Departamento de TI'}
                }
            }
        }
    ],
    'responses': {
        201: {'description': 'Departamento creado'},
        400: {'description': 'Datos inválidos'},
        409: {'description': 'Departamento ya existe'}
    }
})
@requerir_rol('ADMIN')
def registrar_departamento():
    data = request.get_json()

    if not data:
        return respuesta_error("El cuerpo es obligatorio")

    for campo in ['id', 'nombre', 'descripcion']:
        if campo not in data:
            return respuesta_error("Datos incompletos")

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT 1 FROM departamentos WHERE id=%s",
            (data['id'],)
        )
        if cur.fetchone():
            return respuesta_error("El departamento ya existe", 409)

        cur.execute("""
            INSERT INTO departamentos (id, nombre, descripcion)
            VALUES (%s, %s, %s)
        """, (data['id'], data['nombre'], data['descripcion']))

        conn.commit()

        return respuesta_exitosa(
            "Departamento registrado",
            data,
            201
        )

    except Exception as e:
        conn.rollback()
        return respuesta_error(str(e), 500)

    finally:
        cur.close()
        conn.close()

# =========================
# GET /departamentos/{id}
# =========================
@app.route('/departamentos/<id>', methods=['GET'])
@swag_from({
    'tags': ['Departamentos'],
    'description': 'Obtiene un departamento por ID',
    'parameters': [
        {'name': 'id', 'in': 'path', 'type': 'string', 'required': True}
    ],
    'responses': {
        200: {'description': 'Departamento encontrado'},
        404: {'description': 'Departamento no existe'}
    }
})
@requerir_rol('USER', 'ADMIN')
def obtener_departamento(id):
    if os.getenv("CHAOS_LATENCY_ENABLED", "false").lower() == "true" and random.random() < 0.5:
        time.sleep(5)

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, nombre, descripcion FROM departamentos WHERE id=%s",
        (id,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return respuesta_error("Departamento no existe", 404)

    return respuesta_exitosa("Departamento encontrado", {
        "id": row[0],
        "nombre": row[1],
        "descripcion": row[2]
    })

# Ejemplo en Python: latencia artificial para la simulacion de caos.
if random.random() < 0.5:
    time.sleep(5)  # Latencia artificial
# ======================================================
# GET /departamentos (Listado paginado)
# ======================================================
@app.route('/departamentos', methods=['GET'])
@swag_from({
    'tags': ['Departamentos'],
    'description': 'Lista todos los departamentos con paginación',
    'parameters': [
        {
            'name': 'page',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'default': 1,
            'description': 'Número de página'
        },
        {
            'name': 'size',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'default': 10,
            'description': 'Cantidad de registros por página'
        }
    ],
    'responses': {
        200: {
            'description': 'Lista paginada de departamentos'
        }
    }
})
@requerir_rol('USER', 'ADMIN')
def listar_departamentos():
    # =========================
    # 1️⃣ Parámetros de paginación
    # =========================
    page = request.args.get('page', default=1, type=int)
    size = request.args.get('size', default=10, type=int)

    if page < 1 or size < 1:
        return respuesta_error("page y size deben ser mayores que 0")

    offset = (page - 1) * size

    # =========================
    # 2️⃣ Conexión a la BD
    # =========================
    conn = get_db()
    cur = conn.cursor()

    try:
        # =========================
        # 3️⃣ Total de registros
        # =========================
        cur.execute("SELECT COUNT(*) FROM departamentos")
        total_items = cur.fetchone()[0]

        # =========================
        # 4️⃣ Consulta paginada
        # =========================
        cur.execute("""
            SELECT id, nombre, descripcion
            FROM departamentos
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (size, offset))

        departamentos = [
            {
                "id": r[0],
                "nombre": r[1],
                "descripcion": r[2]
            }
            for r in cur.fetchall()
        ]

        # =========================
        # 5️⃣ Metadata de paginación
        # =========================
        total_pages = (total_items + size - 1) // size  # ceil

        return respuesta_exitosa(
            "Lista de departamentos",
            {
                "items": departamentos,
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
# =========================
# Inicializar BD
# =========================
def init_db():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS departamentos (
                id VARCHAR(20) PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                descripcion VARCHAR(255) NOT NULL
            );
        """)
        conn.commit()
        print("Tabla 'departamentos' lista.")
    except Exception as e:
        print(e)
    finally:
        cur.close()
        conn.close()

# =========================
# GET /health
# =========================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8081)
