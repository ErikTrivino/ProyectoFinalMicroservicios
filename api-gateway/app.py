from functools import wraps
import logging
import os

import jwt
import requests
from dotenv import load_dotenv
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
PERFILES_SERVICE_URL = os.getenv("PERFILES_SERVICE_URL", "http://perfiles-service:8083")
VACACIONES_SERVICE_URL = os.getenv("VACACIONES_SERVICE_URL", "http://vacaciones-service")
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


def empleado_id_autenticado():
    payload = getattr(g, "jwt_payload", {})
    return payload.get("empleadoId") or payload.get("empleado_id") or payload.get("id")


@app.get("/health")
def health():
    return respuesta_exitosa("api-gateway OK")


# Operacion expuesta: POST /auth/login (autenticacion).
@app.post("/auth/login")
def login():
    return proxy(AUTH_SERVICE_URL, "/auth/login")


# Operacion expuesta: POST /auth/change-password (usuario autenticado).
@app.post("/auth/change-password")
@requiere_auth()
def change_password():
    return proxy(AUTH_SERVICE_URL, "/auth/change-password")


# Operaciones expuestas: GET/POST /employees.
# GET lista empleados; POST crea empleado (solo ADMIN).
@app.route("/employees", methods=["GET", "POST"])
@requiere_auth("ADMIN", "USER")
def employees():
    if request.method == "POST" and g.jwt_payload.get("role") != "ADMIN":
        return respuesta_error("Permiso denegado", 403)
    return proxy(EMPLEADOS_SERVICE_URL, "/empleados")


# Operaciones expuestas: GET/PUT/DELETE /employees/{id}.
# GET compone "empleado + perfil"; PUT/DELETE actualizan/eliminan empleado (solo ADMIN).
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


# Operaciones expuestas: GET/PUT /profile del empleado autenticado.
@app.route("/profile", methods=["GET", "PUT"])
@requiere_auth("ADMIN", "USER")
def own_profile():
    employee_id = empleado_id_autenticado()
    if not employee_id:
        return respuesta_error("El token no contiene empleadoId", 400)
    return proxy(PERFILES_SERVICE_URL, f"/perfiles/{employee_id}")


# Operaciones expuestas: POST /vacations y GET /vacations.
# POST programa vacaciones; GET consulta vacaciones por cedula.
@app.route("/vacations", methods=["GET", "POST"])
@requiere_auth("ADMIN", "USER")
def vacations():
    if request.method == "POST":
        return proxy(VACACIONES_SERVICE_URL, "/vacaciones")

    cedula = request.args.get("cedula")
    if not cedula:
        employee_id = empleado_id_autenticado()
        if not employee_id:
            return respuesta_error("Use ?cedula=... o autentiquese con un token que tenga empleadoId", 400)
        empleado_response, empleado_body = pedir_json(EMPLEADOS_SERVICE_URL, f"/empleados/{employee_id}")
        if empleado_response.status_code != 200:
            return responder_backend(empleado_response)
        empleado = data_de_respuesta(empleado_body) or {}
        cedula = empleado.get("cedula")

    if not cedula:
        return respuesta_error("No fue posible resolver la cedula del empleado", 400)
    return proxy(VACACIONES_SERVICE_URL, f"/vacaciones/{cedula}")


if __name__ == "__main__":
    # 0.0.0.0 permite exponer el gateway dentro del contenedor.
    # En docker-compose se publica como puerto de entrada para clientes (8088 -> 80).
    app.run(host="0.0.0.0", port=80)
