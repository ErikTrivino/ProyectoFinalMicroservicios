"""
Tests unitarios para empleados-service
Reto 6 - Integración Continua con Jenkins

Estos tests verifican los endpoints del servicio de empleados
utilizando mocking para la base de datos y servicios externos.
"""

import pytest
import json
import jwt
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, date

# Configurar variables de entorno ANTES de importar app
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'test_db'
os.environ['DB_USER'] = 'test_user'
os.environ['DB_PASSWORD'] = 'test_pass'
os.environ['JWT_SECRET'] = 'test-secret-key-for-testing'
os.environ['JWT_ALGORITHM'] = 'HS256'
os.environ['RABBITMQ_HOST'] = 'localhost'
os.environ['RABBITMQ_PORT'] = '5672'
os.environ['RABBITMQ_USER'] = 'admin'
os.environ['RABBITMQ_PASS'] = 'admin'

from app import app, respuesta_exitosa, respuesta_error


# ============================================================
# Fixtures
# ============================================================

JWT_SECRET = 'test-secret-key-for-testing'
JWT_ALGORITHM = 'HS256'


def generar_token(role='ADMIN', expired=False):
    """Genera un JWT token para testing."""
    payload = {
        'sub': 'test_user',
        'role': role,
        'type': 'ACCESS',
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=-1 if expired else 1)
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

class TestHealthCheck:
    """Tests para el endpoint /health."""

    def test_health_check_returns_200(self, client):
        """GET /health debe retornar 200 con status ok."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'


# ============================================================
# Tests de Autenticación
# ============================================================

class TestAutenticacion:
    """Tests para verificar autenticación JWT."""

    @patch('app.get_db')
    def test_request_sin_token_retorna_401(self, mock_db, client):
        """Endpoint protegido sin token debe retornar 401."""
        response = client.get('/empleados')
        assert response.status_code == 401

    @patch('app.get_db')
    def test_request_con_token_invalido_retorna_401(self, mock_db, client):
        """Endpoint protegido con token inválido debe retornar 401."""
        headers = {
            'Authorization': 'Bearer token_invalido',
            'Content-Type': 'application/json'
        }
        response = client.get('/empleados', headers=headers)
        assert response.status_code == 401

    @patch('app.get_db')
    def test_request_con_token_expirado_retorna_401(self, mock_db, client):
        """Endpoint protegido con token expirado debe retornar 401."""
        token = generar_token(expired=True)
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = client.get('/empleados', headers=headers)
        assert response.status_code == 401

    @patch('app.get_db')
    def test_user_no_puede_hacer_post(self, mock_db, client, user_headers):
        """USER no debe poder crear empleados (403)."""
        data = {
            'cedula': '123',
            'nombre': 'Test',
            'email': 'test@test.com',
            'departamentoId': '1',
            'fechaIngreso': '2024-01-01'
        }
        response = client.post('/empleados', headers=user_headers,
                               data=json.dumps(data))
        assert response.status_code == 403

    @patch('app.get_db')
    def test_user_no_puede_hacer_delete(self, mock_db, client, user_headers):
        """USER no debe poder eliminar empleados (403)."""
        response = client.delete('/empleados/some-id', headers=user_headers)
        assert response.status_code == 403


# ============================================================
# Tests de CRUD Empleados
# ============================================================

class TestListarEmpleados:
    """Tests para GET /empleados."""

    @patch('app.get_db')
    def test_listar_empleados_exitoso(self, mock_db, client, admin_headers):
        """GET /empleados con ADMIN debe retornar lista paginada."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock para COUNT
        mock_cursor.fetchone.return_value = (0,)
        # Mock para SELECT
        mock_cursor.fetchall.return_value = []

        response = client.get('/empleados', headers=admin_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'pagination' in data['data']

    @patch('app.get_db')
    def test_listar_empleados_con_user(self, mock_db, client, user_headers):
        """GET /empleados con USER debe funcionar (lectura permitida)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (0,)
        mock_cursor.fetchall.return_value = []

        response = client.get('/empleados', headers=user_headers)
        assert response.status_code == 200

    @patch('app.get_db')
    def test_listar_empleados_paginacion_invalida(self, mock_db, client, admin_headers):
        """GET /empleados con page=0 debe retornar 400."""
        response = client.get('/empleados?page=0&size=10', headers=admin_headers)
        assert response.status_code == 400


class TestObtenerEmpleado:
    """Tests para GET /empleados/{id}."""

    @patch('app.get_db')
    def test_obtener_empleado_existente(self, mock_db, client, admin_headers):
        """GET /empleados/{id} con ID existente debe retornar 200."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (
            'test-id', '12345', 'Juan Pérez', 'juan@test.com', '1',
            date(2024, 1, 1)
        )

        response = client.get('/empleados/test-id', headers=admin_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['nombre'] == 'Juan Pérez'

    @patch('app.get_db')
    def test_obtener_empleado_no_existente(self, mock_db, client, admin_headers):
        """GET /empleados/{id} con ID inexistente debe retornar 404."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = None

        response = client.get('/empleados/no-existe', headers=admin_headers)
        assert response.status_code == 404


class TestRegistrarEmpleado:
    """Tests para POST /empleados."""

    @patch('app.publicar_evento')
    @patch('app.validar_departamento')
    @patch('app.get_db')
    def test_registrar_empleado_exitoso(self, mock_db, mock_validar_dep,
                                        mock_publicar, client, admin_headers):
        """POST /empleados con datos válidos debe retornar 201."""
        mock_validar_dep.return_value = True
        mock_publicar.return_value = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # No existe cedula

        data = {
            'cedula': '12345',
            'nombre': 'Juan Pérez',
            'email': 'juan@test.com',
            'departamentoId': '1',
            'fechaIngreso': '2024-01-01'
        }

        response = client.post('/empleados', headers=admin_headers,
                               data=json.dumps(data))
        assert response.status_code == 201

    @patch('app.get_db')
    def test_registrar_empleado_sin_body(self, mock_db, client, admin_headers):
        """POST /empleados sin body debe retornar 400."""
        response = client.post('/empleados', headers=admin_headers,
                               content_type='application/json')
        assert response.status_code == 400

    @patch('app.get_db')
    def test_registrar_empleado_datos_incompletos(self, mock_db, client, admin_headers):
        """POST /empleados con datos incompletos debe retornar 400."""
        data = {'cedula': '123'}
        response = client.post('/empleados', headers=admin_headers,
                               data=json.dumps(data))
        assert response.status_code == 400

    @patch('app.validar_departamento')
    @patch('app.get_db')
    def test_registrar_empleado_departamento_no_existe(self, mock_db,
                                                        mock_validar_dep, client,
                                                        admin_headers):
        """POST /empleados con departamento inexistente debe retornar 400."""
        mock_validar_dep.return_value = False

        data = {
            'cedula': '12345',
            'nombre': 'Juan',
            'email': 'juan@test.com',
            'departamentoId': '999',
            'fechaIngreso': '2024-01-01'
        }

        response = client.post('/empleados', headers=admin_headers,
                               data=json.dumps(data))
        assert response.status_code == 400

    @patch('app.validar_departamento')
    @patch('app.get_db')
    def test_registrar_empleado_servicio_departamentos_no_disponible(self, mock_db,
                                                                      mock_validar_dep,
                                                                      client,
                                                                      admin_headers):
        """POST /empleados con servicio caído debe retornar 503."""
        mock_validar_dep.return_value = None

        data = {
            'cedula': '12345',
            'nombre': 'Juan',
            'email': 'juan@test.com',
            'departamentoId': '1',
            'fechaIngreso': '2024-01-01'
        }

        response = client.post('/empleados', headers=admin_headers,
                               data=json.dumps(data))
        assert response.status_code == 503

    @patch('app.publicar_evento')
    @patch('app.validar_departamento')
    @patch('app.get_db')
    def test_registrar_empleado_cedula_duplicada(self, mock_db, mock_validar_dep,
                                                  mock_publicar, client,
                                                  admin_headers):
        """POST /empleados con cédula duplicada debe retornar 409."""
        mock_validar_dep.return_value = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)  # Cedula ya existe

        data = {
            'cedula': '12345',
            'nombre': 'Juan',
            'email': 'juan@test.com',
            'departamentoId': '1',
            'fechaIngreso': '2024-01-01'
        }

        response = client.post('/empleados', headers=admin_headers,
                               data=json.dumps(data))
        assert response.status_code == 409


class TestEliminarEmpleado:
    """Tests para DELETE /empleados/{id}."""

    @patch('app.publicar_evento')
    @patch('app.get_db')
    def test_eliminar_empleado_exitoso(self, mock_db, mock_publicar, client,
                                       admin_headers):
        """DELETE /empleados/{id} con ID existente debe retornar 200."""
        mock_publicar.return_value = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            '12345', 'Juan Pérez', 'juan@test.com', '1',
            date(2024, 1, 1)
        )

        response = client.delete('/empleados/test-id', headers=admin_headers)
        assert response.status_code == 200

    @patch('app.get_db')
    def test_eliminar_empleado_no_existente(self, mock_db, client, admin_headers):
        """DELETE /empleados/{id} con ID inexistente debe retornar 404."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        response = client.delete('/empleados/no-existe', headers=admin_headers)
        assert response.status_code == 404


# ============================================================
# Tests de Funciones Auxiliares
# ============================================================

class TestFuncionesAuxiliares:
    """Tests para funciones de respuesta estándar."""

    def test_respuesta_exitosa(self, client):
        """respuesta_exitosa debe retornar formato correcto."""
        with app.test_request_context():
            response, status = respuesta_exitosa("OK", {"key": "value"})
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['message'] == "OK"
            assert data['data']['key'] == "value"
            assert status == 200

    def test_respuesta_error(self, client):
        """respuesta_error debe retornar formato correcto."""
        with app.test_request_context():
            response, status = respuesta_error("Error", 400)
            data = json.loads(response.data)
            assert data['success'] is False
            assert data['message'] == "Error"
            assert status == 400

    def test_respuesta_exitosa_status_personalizado(self, client):
        """respuesta_exitosa con status 201 debe retornar 201."""
        with app.test_request_context():
            response, status = respuesta_exitosa("Creado", None, 201)
            assert status == 201
