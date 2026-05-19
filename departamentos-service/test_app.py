"""
Tests unitarios para departamentos-service
"""

import pytest
import json
import jwt
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Configurar variables de entorno ANTES de importar app
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'test_db'
os.environ['DB_USER'] = 'test_user'
os.environ['DB_PASSWORD'] = 'test_pass'
os.environ['JWT_SECRET'] = 'test-secret-key-for-testing'
os.environ['JWT_ALGORITHM'] = 'HS256'

from app import app, respuesta_exitosa, respuesta_error

JWT_SECRET = 'test-secret-key-for-testing'
JWT_ALGORITHM = 'HS256'


def generar_token(role='ADMIN'):
    """Genera un JWT token para testing."""
    payload = {
        'sub': 'test_user',
        'role': role,
        'type': 'ACCESS',
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def client():
    """Crea un cliente de pruebas Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def admin_headers():
    """Headers con token ADMIN."""
    token = generar_token('ADMIN')
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def user_headers():
    """Headers con token USER."""
    token = generar_token('USER')
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }


# ============================================================
# Tests de Health Check
# ============================================================

def test_health_check_returns_200(client):
    """GET /health debe retornar 200 con status ok."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'ok'


# ============================================================
# Tests de CRUD Departamentos
# ============================================================

@patch('app.get_db')
def test_listar_departamentos_exitoso(mock_db, client, user_headers):
    """GET /departamentos con USER debe retornar lista."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Mock para COUNT
    mock_cursor.fetchone.return_value = (1,)
    # Mock para SELECT
    mock_cursor.fetchall.return_value = [('IT', 'Tecnología', 'Depto de TI')]

    response = client.get('/departamentos', headers=user_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'items' in data['data']
    assert len(data['data']['items']) == 1


@patch('app.get_db')
def test_obtener_departamento_existente(mock_db, client, user_headers):
    """GET /departamentos/{id} debe retornar el departamento."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.return_value = ('IT', 'Tecnología', 'Depto de TI')

    response = client.get('/departamentos/IT', headers=user_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['data']['id'] == 'IT'


@patch('app.get_db')
def test_obtener_departamento_no_existente(mock_db, client, user_headers):
    """GET /departamentos/{id} no existente debe retornar 404."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.return_value = None

    response = client.get('/departamentos/NO_EXISTE', headers=user_headers)
    assert response.status_code == 404


@patch('app.get_db')
def test_registrar_departamento_exitoso(mock_db, client, admin_headers):
    """POST /departamentos con ADMIN debe crear el departamento."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.return_value = None  # No existe

    data = {
        'id': 'HR',
        'nombre': 'Recursos Humanos',
        'descripcion': 'Depto de RRHH'
    }
    response = client.post('/departamentos', 
                           headers=admin_headers,
                           data=json.dumps(data))
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['success'] is True


@patch('app.get_db')
def test_registrar_departamento_user_denegado(mock_db, client, user_headers):
    """POST /departamentos con USER debe retornar 403."""
    data = {
        'id': 'HR',
        'nombre': 'Recursos Humanos',
        'descripcion': 'Depto de RRHH'
    }
    response = client.post('/departamentos', 
                           headers=user_headers,
                           data=json.dumps(data))
    
    assert response.status_code == 403
