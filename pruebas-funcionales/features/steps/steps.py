import requests
import time
from behave import given, when, then

# --- Helpers ---

def get_token(context, username, password):
    url = f"{context.base_url_auth}/auth/login"
    payload = {"username": username, "password": password}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()['data']['access_token']
    return None

def poll_notifications(context, email, timeout=15):
    """Polling function to find the reset token for a new user"""
    url = f"{context.base_url_notificaciones}/notificaciones"
    start_time = time.time()
    
    # Necesitamos un token (admin o user) para consultar notificaciones según index.js
    token = get_token(context, context.admin_user, context.admin_pass)
    headers = {"Authorization": f"Bearer {token}"}
    
    while time.time() - start_time < timeout:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            json_response = response.json()
            # Extraer las notificaciones del campo 'data' envuelto por el ApiResponse
            notifications = json_response.get('data', [])
            # Buscar la notificación de SEGURIDAD para el email dado
            for notif in notifications:
                if notif['destinatario'] == email and notif['tipo'] == 'SEGURIDAD':
                    # Extraer token del mensaje: "Para establecer o recuperar su contraseña, utilice el token: <TOKEN>"
                    msg = notif['mensaje']
                    if "token: " in msg:
                        return msg.split("token: ")[1].strip()
        time.sleep(2)
    return None

# --- Pasos de Gherkin ---

@given('que el sistema está operativo')
def step_system_up(context):
    response = requests.get(f"{context.base_url_auth}/health")
    assert response.status_code == 200

@given('que estoy autenticado como "{role}"')
def step_auth_as(context, role):
    if role == "ADMIN":
        context.token = get_token(context, context.admin_user, context.admin_pass)
    elif role == "USER":
        context.token = get_token(context, context.default_user, context.default_pass)
    else:
        # Para usuarios creados dinámicamente
        user_data = getattr(context, 'new_user', {})
        context.token = get_token(context, user_data.get('username'), user_data.get('password'))
    
    assert context.token is not None, f"No se pudo obtener token para el rol {role}"

@given('que no tengo un token de autenticación')
def step_no_token(context):
    context.token = None

@given('que tengo un token inválido')
def step_invalid_token(context):
    context.token = "token_totalmente_invalido_123"

@when('intento consultar la lista de empleados')
def step_get_empleados(context):
    headers = {}
    if getattr(context, 'token', None):
        headers["Authorization"] = f"Bearer {context.token}"
    
    context.last_response = requests.get(f"{context.base_url_empleados}/empleados", headers=headers)

@when('el administrador registra un nuevo empleado con nombre "{nombre}" y email "{email}"')
def step_register_employee(context, nombre, email):
    # Generar un sufijo único para evitar conflictos entre las 3 ejecuciones
    timestamp = str(int(time.time()))[-6:]
    
    # Reformatear email y username para ser únicos
    # En este sistema, el username es el email completo (según auth-service/app.py:261)
    parts = email.split('@')
    unique_email = f"{parts[0]}_{timestamp}@{parts[1]}"
    unique_username = unique_email
    
    # Guardamos datos para pasos posteriores
    context.new_user_email = unique_email
    context.new_user_username = unique_username
    
    # Payload completo según requiere empleados-service (app.py:262)
    payload = {
        "cedula": f"ID-{timestamp}", # Requerido
        "nombre": f"{nombre} {timestamp}",
        "email": unique_email,
        "departamentoId": "D001", # Corregido campo (CamelCase)
        "fechaIngreso": time.strftime("%Y-%m-%d") # Requerido
    }
    
    admin_token = get_token(context, context.admin_user, context.admin_pass)
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    context.last_response = requests.post(f"{context.base_url_empleados}/empleados", json=payload, headers=headers)
    
    # Mostrar error si falla
    assert context.last_response.status_code == 201, \
        f"Fallo al crear empleado: {context.last_response.text}"
        
    context.new_user_id = context.last_response.json()['data']['id']

@when('espero la notificación y activo la cuenta con la nueva contraseña "{password}"')
def step_poll_and_activate(context, password):
    # Polling para el token de reset
    reset_token = poll_notifications(context, context.new_user_email)
    assert reset_token is not None, f"El token de activación para {context.new_user_email} no llegó a tiempo"
    
    # Reset password en auth-service
    url = f"{context.base_url_auth}/auth/reset-password"
    payload = {"token": reset_token, "newPassword": password}
    response = requests.post(url, json=payload)
    assert response.status_code == 200
    
    # Guardar credenciales para login
    context.new_user_password = password

@step('el nuevo empleado intenta iniciar sesión')
def step_new_user_login(context):
    url = f"{context.base_url_auth}/auth/login"
    payload = {
        "username": context.new_user_username,
        "password": context.new_user_password
    }
    context.last_response = requests.post(url, json=payload)

@given('que existe un empleado activo con nombre "{nombre}" y email "{email}"')
def step_ensure_employee(context, nombre, email):
    step_register_employee(context, nombre, email)
    step_poll_and_activate(context, "TempPass123!")

@when('el administrador elimina al empleado recién creado')
def step_delete_current(context):
    admin_token = get_token(context, context.admin_user, context.admin_pass)
    headers = {"Authorization": f"Bearer {admin_token}"}
    context.last_response = requests.delete(f"{context.base_url_empleados}/empleados/{context.new_user_id}", headers=headers)

@step('el empleado desvinculado intenta iniciar sesión')
def step_deleted_login(context):
    url = f"{context.base_url_auth}/auth/login"
    payload = {
        "username": context.new_user_username,
        "password": context.new_user_password
    }
    context.last_response = requests.post(url, json=payload)

@when('intento registrar un empleado con datos inválidos')
def step_register_invalid(context):
    admin_token = get_token(context, context.admin_user, context.admin_pass)
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    # Faltan campos obligatorios para provocar el 400
    payload = {"nombre": "Invalido"} 
    context.last_response = requests.post(f"{context.base_url_empleados}/empleados", json=payload, headers=headers)

@then('el sistema responde con un código de estado {status:d}')
def step_check_status(context, status):
    assert context.last_response.status_code == status, \
        f"Esperaba {status} pero recibí {context.last_response.status_code}. Respuesta: {context.last_response.text}"

@then('la respuesta debe contener un token de acceso')
def step_check_token_in_res(context):
    data = context.last_response.json()
    assert 'access_token' in data['data'], "No se encontró access_token en la respuesta"

@then('puedo ver los detalles del empleado en la lista')
def step_verify_in_list(context):
    # Aquí podríamos verificar que el nombre/email aparece en la lista de empleados
    headers = {"Authorization": f"Bearer {context.token}"}
    res = requests.get(f"{context.base_url_empleados}/empleados", headers=headers)
    found = any(e['email'] == context.new_user_email for e in res.json()['data'])
    assert found, f"Empleado {context.new_user_email} no encontrado en la lista"

# --- Pasos para Perfiles ---

@when('intento consultar la lista de perfiles')
def step_get_perfiles(context):
    headers = {"Authorization": f"Bearer {context.token}"}
    context.last_response = requests.get(f"{context.base_url_perfiles}/perfiles", headers=headers)

@when('intento consultar el perfil del empleado recién creado')
def step_get_perfil_by_id(context):
    headers = {"Authorization": f"Bearer {context.token}"}
    url = f"{context.base_url_perfiles}/perfiles/{context.new_user_id}"
    context.last_response = requests.get(url, headers=headers)

@when('actualizo el perfil del empleado con biografía "{biografia}" y experiencia "{experiencia}"')
def step_update_perfil(context, biografia, experiencia):
    headers = {"Authorization": f"Bearer {context.token}", "Content-Type": "application/json"}
    payload = {
        "biografia": biografia,
        "experiencia": experiencia,
        "especialidades": ["Testing", "Automation"],
        "redesSociales": {"github": "testuser"}
    }
    url = f"{context.base_url_perfiles}/perfiles/{context.new_user_id}"
    context.last_response = requests.put(url, json=payload, headers=headers)

@then('la respuesta contiene una lista de perfiles')
def step_check_perfiles_list(context):
    data = context.last_response.json()
    assert data['success'] is True
    assert isinstance(data['data'], list)

@then('los detalles del perfil corresponden al empleado creado')
def step_verify_perfil_details(context):
    data = context.last_response.json()['data']
    assert data['empleadoId'] == context.new_user_id

@then('el perfil actualizado muestra la nueva biografía y experiencia')
def step_verify_updated_perfil(context):
    data = context.last_response.json()['data']
    assert data['biografia'] == "Experta en microservicios"
    assert data['experiencia'] == "5 años"
