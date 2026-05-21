from functools import wraps
import logging
import os

import jwt
import requests
from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask, Response, g, jsonify, request
from opentelemetry import trace
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_flask_exporter import PrometheusMetrics
from pythonjsonlogger import jsonlogger

load_dotenv()

app = Flask(__name__)

swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "API Gateway - CheckIn Microservicios",
        "description": (
            "Punto unico de entrada para autenticacion, empleados, perfiles y vacaciones. "
            "El gateway valida JWT y reenvia solicitudes a los microservicios internos."
        ),
        "version": "1.0.0",
    },
    "basePath": "/",
    "schemes": ["http"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT usando el esquema Bearer. Ejemplo: Authorization: Bearer {token}",
        }
    },
    "tags": [
        {"name": "Auth", "description": "Autenticacion y credenciales"},
        {"name": "Empleados", "description": "Gestion de empleados"},
        {"name": "Departamentos", "description": "Gestion de departamentos"},
        {"name": "Perfiles", "description": "Gestion de perfiles"},
        {"name": "Vacaciones", "description": "Gestion de vacaciones"},
        {"name": "Notificaciones", "description": "Consulta de notificaciones"},
    ],
    "definitions": {
        "ApiResponse": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"},
                "data": {"type": "object"},
            },
        },
        "LoginRequest": {
            "type": "object",
            "required": ["username", "password"],
            "properties": {
                "username": {"type": "string", "example": "admin"},
                "password": {"type": "string", "example": "admin123"},
            },
        },
        "ChangePasswordRequest": {
            "type": "object",
            "required": ["current_password", "new_password"],
            "properties": {
                "current_password": {"type": "string", "example": "admin123"},
                "new_password": {"type": "string", "example": "Nuevo123!"},
            },
        },
        "EmployeeRequest": {
            "type": "object",
            "required": ["cedula", "nombre", "email", "departamentoId"],
            "properties": {
                "cedula": {"type": "string", "example": "123456789"},
                "nombre": {"type": "string", "example": "Ana Gomez"},
                "email": {"type": "string", "example": "ana.gomez@empresa.com"},
                "departamentoId": {"type": "string", "example": "IT"},
                "fechaIngreso": {"type": "string", "format": "date", "example": "2026-05-20"},
                "password": {"type": "string", "example": "Vac12345!"},
            },
        },
        "DepartmentRequest": {
            "type": "object",
            "required": ["id", "nombre", "descripcion"],
            "properties": {
                "id": {"type": "string", "example": "IT"},
                "nombre": {"type": "string", "example": "Tecnologia"},
                "descripcion": {"type": "string", "example": "Departamento de TI"},
            },
        },
        "ProfileRequest": {
            "type": "object",
            "properties": {
                "telefono": {"type": "string", "example": "3001234567"},
                "direccion": {"type": "string", "example": "Calle 123"},
                "cargo": {"type": "string", "example": "Analista"},
            },
        },
        "VacationRequest": {
            "type": "object",
            "required": ["cedula", "fecha_inicio", "fecha_fin"],
            "properties": {
                "cedula": {"type": "string", "example": "123456789"},
                "fecha_inicio": {"type": "string", "format": "date", "example": "2026-06-10"},
                "fecha_fin": {"type": "string", "format": "date", "example": "2026-06-15"},
            },
        },
    },
    "paths": {
        "/auth/login": {"post": {"tags": ["Auth"], "summary": "Inicia sesion y obtiene un JWT", "parameters": [{"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/LoginRequest"}}], "responses": {"200": {"description": "Login exitoso"}, "401": {"description": "Credenciales invalidas"}}}},
        "/auth/change-password": {"post": {"tags": ["Auth"], "summary": "Cambia la contrasena del usuario autenticado", "security": [{"Bearer": []}], "parameters": [{"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/ChangePasswordRequest"}}], "responses": {"200": {"description": "Contrasena actualizada"}, "401": {"description": "Token invalido o ausente"}}}},
        "/empleados": {
            "get": {"tags": ["Empleados"], "summary": "Lista empleados con paginacion", "security": [{"Bearer": []}], "parameters": [{"in": "query", "name": "page", "type": "integer", "required": False, "default": 1}, {"in": "query", "name": "size", "type": "integer", "required": False, "default": 10}], "responses": {"200": {"description": "Lista paginada de empleados"}}},
            "post": {"tags": ["Empleados"], "summary": "Crea un empleado", "description": "Operacion permitida solo para rol ADMIN.", "security": [{"Bearer": []}], "parameters": [{"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/EmployeeRequest"}}], "responses": {"201": {"description": "Empleado creado"}, "403": {"description": "Permiso denegado"}}},
        },
        "/empleados/{id}": {
            "get": {"tags": ["Empleados"], "summary": "Obtiene un empleado con su perfil", "security": [{"Bearer": []}], "parameters": [{"in": "path", "name": "id", "type": "string", "required": True}], "responses": {"200": {"description": "Empleado completo"}, "404": {"description": "Empleado no encontrado"}}},
            "put": {"tags": ["Empleados"], "summary": "Actualiza un empleado", "security": [{"Bearer": []}], "parameters": [{"in": "path", "name": "id", "type": "string", "required": True}, {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/EmployeeRequest"}}], "responses": {"200": {"description": "Empleado actualizado"}}},
            "delete": {"tags": ["Empleados"], "summary": "Elimina un empleado", "security": [{"Bearer": []}], "parameters": [{"in": "path", "name": "id", "type": "string", "required": True}], "responses": {"200": {"description": "Empleado eliminado"}}},
        },
        "/departamentos": {
            "get": {"tags": ["Departamentos"], "summary": "Lista departamentos con paginacion", "security": [{"Bearer": []}], "parameters": [{"in": "query", "name": "page", "type": "integer", "required": False, "default": 1}, {"in": "query", "name": "size", "type": "integer", "required": False, "default": 10}], "responses": {"200": {"description": "Lista paginada de departamentos"}}},
            "post": {"tags": ["Departamentos"], "summary": "Crea un departamento", "description": "Operacion permitida solo para rol ADMIN.", "security": [{"Bearer": []}], "parameters": [{"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/DepartmentRequest"}}], "responses": {"201": {"description": "Departamento creado"}}},
        },
        "/departamentos/{id}": {"get": {"tags": ["Departamentos"], "summary": "Obtiene un departamento por id", "security": [{"Bearer": []}], "parameters": [{"in": "path", "name": "id", "type": "string", "required": True}], "responses": {"200": {"description": "Departamento encontrado"}, "404": {"description": "Departamento no encontrado"}}}},
        "/perfiles": {"get": {"tags": ["Perfiles"], "summary": "Lista perfiles", "security": [{"Bearer": []}], "responses": {"200": {"description": "Lista de perfiles"}}}},
        "/perfiles/{empleadoId}": {
            "get": {"tags": ["Perfiles"], "summary": "Consulta perfil por empleadoId", "security": [{"Bearer": []}], "parameters": [{"in": "path", "name": "empleadoId", "type": "string", "required": True}], "responses": {"200": {"description": "Perfil encontrado"}, "404": {"description": "Perfil no encontrado"}}},
            "put": {"tags": ["Perfiles"], "summary": "Actualiza perfil por empleadoId", "security": [{"Bearer": []}], "parameters": [{"in": "path", "name": "empleadoId", "type": "string", "required": True}, {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/ProfileRequest"}}], "responses": {"200": {"description": "Perfil actualizado"}}},
        },
        "/vacaciones": {"post": {"tags": ["Vacaciones"], "summary": "Programa vacaciones", "security": [{"Bearer": []}], "parameters": [{"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/VacationRequest"}}], "responses": {"201": {"description": "Vacaciones programadas"}}}},
        "/vacaciones/{cedula}": {"get": {"tags": ["Vacaciones"], "summary": "Consulta vacaciones por cedula", "security": [{"Bearer": []}], "parameters": [{"in": "path", "name": "cedula", "type": "string", "required": True}], "responses": {"200": {"description": "Historial de vacaciones"}}}},
        "/vacaciones/{id}/estado": {"put": {"tags": ["Vacaciones"], "summary": "Actualiza estado de vacaciones", "security": [{"Bearer": []}], "parameters": [{"in": "path", "name": "id", "type": "integer", "required": True}, {"in": "body", "name": "body", "required": True, "schema": {"type": "object", "required": ["estado"], "properties": {"estado": {"type": "string", "example": "Cancelada"}}}}], "responses": {"200": {"description": "Estado actualizado"}}}},
        "/notificaciones": {"get": {"tags": ["Notificaciones"], "summary": "Lista notificaciones", "security": [{"Bearer": []}], "responses": {"200": {"description": "Lista de notificaciones"}}}},
        "/notificaciones/{empleadoId}": {"get": {"tags": ["Notificaciones"], "summary": "Lista notificaciones por empleadoId", "security": [{"Bearer": []}], "parameters": [{"in": "path", "name": "empleadoId", "type": "string", "required": True}], "responses": {"200": {"description": "Notificaciones del empleado"}, "404": {"description": "Sin notificaciones"}}}},
    },
})

logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

provider = TracerProvider(resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "api-gateway")}))
provider.add_span_processor(BatchSpanProcessor(ZipkinExporter(endpoint=os.getenv("ZIPKIN_ENDPOINT", "http://zipkin:9411/api/v2/spans"))))
trace.set_tracer_provider(provider)

metrics = PrometheusMetrics(app)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretosupersecretosupersecreto")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service")
EMPLEADOS_SERVICE_URL = os.getenv("EMPLEADOS_SERVICE_URL", "http://empleados-service")
DEPARTAMENTOS_SERVICE_URL = os.getenv("DEPARTAMENTOS_SERVICE_URL", "http://departamentos-service:8081")
PERFILES_SERVICE_URL = os.getenv("PERFILES_SERVICE_URL", "http://perfiles-service:8083")
VACACIONES_SERVICE_URL = os.getenv("VACACIONES_SERVICE_URL", "http://vacaciones-service")
NOTIFICACIONES_SERVICE_URL = os.getenv("NOTIFICACIONES_SERVICE_URL", "http://notificaciones-service:8084")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "8"))


def respuesta_exitosa(mensaje, data=None, status=200):
    return jsonify({"success": True, "message": mensaje, "data": data}), status


def respuesta_error(mensaje, status=400):
    return jsonify({"success": False, "message": mensaje, "data": None}), status


def obtener_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()


def validar_token():
    # Validacion JWT centralizada en gateway para rutas protegidas.
    token = obtener_token()
    if not token:
        return None, respuesta_error("Authorization header missing or malformed", 401)
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "ACCESS":
            return None, respuesta_error("Token de acceso invalido", 401)
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, respuesta_error("Token expirado", 401)
    except jwt.InvalidTokenError:
        return None, respuesta_error("Token invalido", 401)


def requiere_auth(*roles):
    # Decorador RBAC: exige token valido y, opcionalmente, rol permitido.
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            payload, error = validar_token()
            if error:
                return error
            if roles and payload.get("role") not in roles:
                return respuesta_error("Permiso denegado", 403)
            g.jwt_payload = payload
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def headers_para_backend():
    excluded = {"host", "content-length", "connection"}
    return {key: value for key, value in request.headers.items() if key.lower() not in excluded}


def responder_backend(response):
    excluded = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    headers = [(key, value) for key, value in response.headers.items() if key.lower() not in excluded]
    return Response(response.content, response.status_code, headers)


def proxy(base_url, path):
    # Enrutamiento del API Gateway: reenvia la solicitud al microservicio destino.
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        response = requests.request(
            method=request.method,
            url=url,
            headers=headers_para_backend(),
            params=request.args,
            data=request.get_data(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        return responder_backend(response)
    except requests.RequestException:
        logger.exception("Error llamando backend %s", url)
        return respuesta_error("Servicio no disponible", 503)


def pedir_json(base_url, path):
    response = requests.get(
        f"{base_url.rstrip('/')}/{path.lstrip('/')}",
        headers=headers_para_backend(),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    try:
        body = response.json()
    except ValueError:
        body = None
    return response, body


def data_de_respuesta(body):
    if isinstance(body, dict) and "data" in body:
        return body.get("data")
    return body


# Operacion expuesta: POST /auth/login (autenticacion).
@app.post("/auth/login")
def login():
    return proxy(AUTH_SERVICE_URL, "/auth/login")


# Operacion expuesta: POST /auth/change-password (usuario autenticado).
@app.post("/auth/change-password")
@requiere_auth()
def change_password():
    return proxy(AUTH_SERVICE_URL, "/auth/change-password")


# Operaciones expuestas: GET/POST /empleados y /employees.
# GET lista empleados; POST crea empleado (solo ADMIN).
@app.route("/empleados", methods=["GET", "POST"])
@app.route("/employees", methods=["GET", "POST"])
@requiere_auth("ADMIN", "USER")
def employees():
    if request.method == "POST" and g.jwt_payload.get("role") != "ADMIN":
        return respuesta_error("Permiso denegado", 403)
    return proxy(EMPLEADOS_SERVICE_URL, "/empleados")


# Operaciones expuestas: GET/PUT/DELETE /empleados/{id} y /employees/{id}.
# GET compone "empleado + perfil"; PUT/DELETE actualizan/eliminan empleado (solo ADMIN).
@app.route("/empleados/<employee_id>", methods=["GET", "PUT", "DELETE"])
@app.route("/employees/<employee_id>", methods=["GET", "PUT", "DELETE"])
@requiere_auth("ADMIN", "USER")
def employee_by_id(employee_id):
    if request.method in {"PUT", "DELETE"} and g.jwt_payload.get("role") != "ADMIN":
        return respuesta_error("Permiso denegado", 403)
    if request.method != "GET":
        return proxy(EMPLEADOS_SERVICE_URL, f"/empleados/{employee_id}")

    # Composicion de respuesta desde dos microservicios:
    # - empleados-service -> datos base del empleado
    # - perfiles-service  -> perfil del empleado
    empleado_response, empleado_body = pedir_json(EMPLEADOS_SERVICE_URL, f"/empleados/{employee_id}")
    if empleado_response.status_code != 200:
        return responder_backend(empleado_response)

    perfil_response, perfil_body = pedir_json(PERFILES_SERVICE_URL, f"/perfiles/{employee_id}")
    perfil = None if perfil_response.status_code == 404 else data_de_respuesta(perfil_body)
    if perfil_response.status_code not in (200, 404):
        return responder_backend(perfil_response)

    return respuesta_exitosa("Empleado completo", {
        "employee": data_de_respuesta(empleado_body),
        "profile": perfil,
    })


# Operaciones expuestas: GET/POST /departamentos.
# GET lista departamentos; POST crea departamento (solo ADMIN).
@app.route("/departamentos", methods=["GET", "POST"])
@requiere_auth("ADMIN", "USER")
def departments():
    if request.method == "POST" and g.jwt_payload.get("role") != "ADMIN":
        return respuesta_error("Permiso denegado", 403)
    return proxy(DEPARTAMENTOS_SERVICE_URL, "/departamentos")


# Operacion expuesta: GET /departamentos/{id}.
@app.get("/departamentos/<department_id>")
@requiere_auth("ADMIN", "USER")
def department_by_id(department_id):
    return proxy(DEPARTAMENTOS_SERVICE_URL, f"/departamentos/{department_id}")


# Operacion expuesta: GET /perfiles.
@app.get("/perfiles")
@requiere_auth("ADMIN", "USER")
def profiles():
    return proxy(PERFILES_SERVICE_URL, "/perfiles")


# Operaciones expuestas: GET/PUT /perfiles/{empleadoId}.
@app.route("/perfiles/<employee_id>", methods=["GET", "PUT"])
@requiere_auth("ADMIN", "USER")
def profile_by_employee_id(employee_id):
    return proxy(PERFILES_SERVICE_URL, f"/perfiles/{employee_id}")


# Operaciones expuestas: GET/PUT /profile (del usuario autenticado).
@app.route("/profile", methods=["GET", "PUT"])
@requiere_auth("ADMIN", "USER")
def profile_self():
    emp_id = g.jwt_payload.get("empleadoId")
    if not emp_id:
        return respuesta_error("ID de empleado no encontrado en el token", 400)
    return proxy(PERFILES_SERVICE_URL, f"/perfiles/{emp_id}")


# Operacion expuesta: POST /vacaciones y /vacations.
@app.route("/vacaciones", methods=["POST"])
@app.route("/vacations", methods=["POST"])
@requiere_auth("ADMIN", "USER")
def create_vacation():
    return proxy(VACACIONES_SERVICE_URL, "/vacaciones")


# Operacion expuesta: GET /vacaciones/{cedula} y /vacations/{cedula}.
@app.route("/vacaciones/<cedula>", methods=["GET"])
@app.route("/vacations/<cedula>", methods=["GET"])
@requiere_auth("ADMIN", "USER")
def vacations_by_employee(cedula):
    return proxy(VACACIONES_SERVICE_URL, f"/vacaciones/{cedula}")


# Operacion expuesta: GET /vacations (para el usuario autenticado).
@app.route("/vacations", methods=["GET"])
@requiere_auth("ADMIN", "USER")
def vacations_self():
    emp_id = g.jwt_payload.get("empleadoId")
    if not emp_id:
        return respuesta_error("ID de empleado no encontrado en el token", 400)
    
    # Obtener el empleado para saber su cedula
    response, body = pedir_json(EMPLEADOS_SERVICE_URL, f"/empleados/{emp_id}")
    if response.status_code != 200:
        return responder_backend(response)
    
    emp_data = data_de_respuesta(body)
    cedula = emp_data.get("cedula")
    if not cedula:
        return respuesta_error("Cedula de empleado no encontrada", 404)
        
    return proxy(VACACIONES_SERVICE_URL, f"/vacaciones/{cedula}")


# Operacion expuesta: PUT /vacaciones/{id}/estado y /vacations/{id}/status.
@app.route("/vacaciones/<vacation_id>/estado", methods=["PUT"])
@app.route("/vacations/<vacation_id>/status", methods=["PUT"])
@requiere_auth("ADMIN", "USER")
def update_vacation_status(vacation_id):
    return proxy(VACACIONES_SERVICE_URL, f"/vacaciones/{vacation_id}/estado")


# Operacion expuesta: GET /notificaciones.
@app.get("/notificaciones")
@requiere_auth("ADMIN", "USER")
def notifications():
    return proxy(NOTIFICACIONES_SERVICE_URL, "/notificaciones")


# Operacion expuesta: GET /notificaciones/{empleadoId}.
@app.get("/notificaciones/<employee_id>")
@requiere_auth("ADMIN", "USER")
def notifications_by_employee(employee_id):
    return proxy(NOTIFICACIONES_SERVICE_URL, f"/notificaciones/{employee_id}")


# Operacion expuesta: GET /health.
@app.get("/health")
def health():
    dependencies = {}
    services = {
        "auth-service": AUTH_SERVICE_URL,
        "empleados-service": EMPLEADOS_SERVICE_URL,
        "departamentos-service": DEPARTAMENTOS_SERVICE_URL,
        "perfiles-service": PERFILES_SERVICE_URL,
        "vacaciones-service": VACACIONES_SERVICE_URL,
        "notificaciones-service": NOTIFICACIONES_SERVICE_URL
    }
    
    overall_ok = True
    for name, url_base in services.items():
        url = f"{url_base.rstrip('/')}/health"
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                dependencies[name] = {"status": "UP"}
            else:
                dependencies[name] = {"status": "DEGRADED", "code": resp.status_code}
        except Exception as e:
            overall_ok = False
            dependencies[name] = {"status": "DOWN", "error": str(e)}
            
    return jsonify({
        "status": "UP" if overall_ok else "DEGRADED",
        "dependencies": dependencies
    }), 200 if overall_ok else 500


if __name__ == "__main__":
    # 0.0.0.0 permite exponer el gateway dentro del contenedor.
    # En docker-compose se publica como puerto de entrada para clientes (8088 -> 80).
    app.run(host="0.0.0.0", port=80)
