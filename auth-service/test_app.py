"""
Tests unitarios para auth-service
"""

import pytest
import json
import jwt
import os
import datetime
from unittest.mock import patch, MagicMock

# Configurar variables de entorno ANTES de importar app
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'test_db'
os.environ['DB_USER'] = 'test_user'
os.environ['DB_PASSWORD'] = 'test_pass'
os.environ['JWT_SECRET'] = 'test-secret-key-for-testing'
os.environ['JWT_ALGORITHM'] = 'HS256'
os.environ['RABBITMQ_URL'] = 'amqp://guest:guest@localhost:5672'

from app import app, respuesta_exitosa, respuesta_error, crear_token


@pytest.fixture
def client():
    """Crea un cliente de pruebas Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# ============================================================
# Tests de Health Check
# ============================================================

def test_health_check_returns_200(client):
    """GET /health debe retornar 200 con status ok."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['message'] == 'auth-service OK'


# ============================================================
# Tests de Autenticación / Login
# ============================================================

@patch('app.obtener_usuario_por_username')
def test_login_exitoso(mock_obtener_usuario, client):
    """POST /auth/login con credenciales válidas debe retornar token."""
    # Mock de usuario: id, username, email, password_hash, role, active, empleado_id
    # Usamos hash de 'admin123'
    import bcrypt
    password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    mock_obtener_usuario.return_value = (1, 'admin', 'admin@empresa.com', password_hash, 'ADMIN', True, 'admin-id')

    data = {
        'username': 'admin',
        'password': 'admin123'
    }
    response = client.post('/auth/login', 
                           data=json.dumps(data),
                           content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'access_token' in data['data']
    assert data['data']['role'] == 'ADMIN'


@patch('app.obtener_usuario_por_username')
def test_login_usuario_no_existe(mock_obtener_usuario, client):
    """POST /auth/login con usuario inexistente debe retornar 401."""
    mock_obtener_usuario.return_value = None

    data = {
        'username': 'noexiste',
        'password': 'password'
    }
    response = client.post('/auth/login', 
                           data=json.dumps(data),
                           content_type='application/json')
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['message'] == 'Credenciales inválidas'


# ============================================================
# Tests de Validación de Token
# ============================================================

def test_validate_token_valido(client):
    """POST /auth/validate con token válido debe retornar 200."""
    token = crear_token({"sub": "admin", "role": "ADMIN", "type": "ACCESS"}, datetime.timedelta(minutes=10))
    
    data = {'token': token}
    response = client.post('/auth/validate', 
                           data=json.dumps(data),
                           content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['message'] == 'Token válido'


def test_validate_token_invalido(client):
    """POST /auth/validate con token inválido debe retornar 401."""
    data = {'token': 'token_invalido'}
    response = client.post('/auth/validate', 
                           data=json.dumps(data),
                           content_type='application/json')
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['message'] == 'Token inválido'


# ============================================================
# Tests de Recuperación de Contraseña
# ============================================================

@patch('app.publicar_evento')
@patch('app.obtener_usuario_por_email')
def test_recover_password_exitoso(mock_obtener_usuario, mock_publicar, client):
    """POST /auth/recover-password debe enviar evento si el email existe."""
    mock_obtener_usuario.return_value = (1, 'admin', 'admin@empresa.com', 'hash', 'ADMIN', True, 'admin-id')
    mock_publicar.return_value = True

    data = {'email': 'admin@empresa.com'}
    response = client.post('/auth/recover-password', 
                           data=json.dumps(data),
                           content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert mock_publicar.called
