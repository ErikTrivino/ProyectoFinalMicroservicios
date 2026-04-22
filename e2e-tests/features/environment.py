import os
from dotenv import load_dotenv

def before_all(context):
    # Cargar variables de entorno desde .env
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    
    context.base_url_auth = os.getenv('AUTH_URL')
    context.base_url_empleados = os.getenv('EMPLEADOS_URL')
    context.base_url_notificaciones = os.getenv('NOTIFICACIONES_URL')
    context.base_url_departamentos = os.getenv('DEPARTAMENTOS_URL')
    
    context.admin_user = os.getenv('ADMIN_USER')
    context.admin_pass = os.getenv('ADMIN_PASS')
    context.default_user = os.getenv('DEFAULT_USER')
    context.default_pass = os.getenv('DEFAULT_PASS')
    
    import requests
    context.session = requests.Session()

    # --- Asegurar precondiciones globales ---
    # 1. Obtener token admin
    login_url = f"{context.base_url_auth}/auth/login"
    res = requests.post(login_url, json={"username": context.admin_user, "password": context.admin_pass})
    if res.status_code == 200:
        token = res.json()['data']['access_token']
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # 2. Crear departamento de prueba si no existe
        dept_payload = {
            "id": "D001",
            "nombre": "Departamento de Pruebas",
            "descripcion": "Creado automáticamente por la suite de pruebas E2E"
        }
        requests.post(f"{context.base_url_departamentos}/departamentos", json=dept_payload, headers=headers)

def after_scenario(context, scenario):
    # Limpiar tokens u otra data después de cada escenario
    if hasattr(context, 'token'):
        del context.token
    if hasattr(context, 'last_response'):
        del context.last_response
