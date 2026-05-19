#!/bin/bash

# Script de Pruebas Rápidas - Microservicios JWT
# Uso: bash test-api.sh

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Pruebas de Microservicios JWT${NC}"
echo -e "${BLUE}========================================${NC}\n"

# URLs base
AUTH_URL="http://localhost:8082"
EMPLEADOS_URL="http://localhost:8080"

# Variables globales
ADMIN_TOKEN=""
USER_TOKEN=""

# Función de utilidad para hacer requests
function make_request() {
    local method=$1
    local endpoint=$2
    local url=$3
    local data=$4
    local token=$5

    if [ -z "$token" ]; then
        curl -s -X "$method" "$url$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$url$endpoint" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $token" \
            -d "$data"
    fi
}

# Función de prueba
function test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local url=$4
    local data=$5
    local token=$6
    local expected_status=$7

    echo -e "${YELLOW}[TEST]${NC} $name"
    
    response=$(make_request "$method" "$endpoint" "$url" "$data" "$token")
    status=$(echo "$response" | tail -n1)
    
    if [[ "$response" == *"success"* ]]; then
        echo -e "${GREEN}✓ PASSED${NC}\n"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
        echo ""
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
        echo ""
    fi
}

# ==================== PRUEBA 1: Health Check ====================
echo -e "${BLUE}1. Health Check${NC}"
echo "---"
HEALTH=$(curl -s -X GET "$AUTH_URL/health" -H "Content-Type: application/json")
echo "$HEALTH" | jq '.'
echo ""

# ==================== PRUEBA 2: Registrar Usuario ====================
echo -e "${BLUE}2. Registrar Usuario${NC}"
echo "---"
REGISTER_DATA='{
  "username": "test_user",
  "email": "test@ejemplo.com",
  "password": "TestPass123"
}'
REGISTER_RESPONSE=$(curl -s -X POST "$AUTH_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "$REGISTER_DATA")
echo "$REGISTER_RESPONSE" | jq '.'
echo ""

# ==================== PRUEBA 3: Login ADMIN ====================
echo -e "${BLUE}3. Login como ADMIN (Por Defecto)${NC}"
echo "---"
LOGIN_ADMIN='{
  "username": "admin",
  "password": "admin123"
}'
LOGIN_RESPONSE=$(curl -s -X POST "$AUTH_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "$LOGIN_ADMIN")
echo "$LOGIN_RESPONSE" | jq '.'
ADMIN_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.data.access_token')
echo ""

# ==================== PRUEBA 4: Login Usuario Registrado ====================
echo -e "${BLUE}4. Login como USER (Registrado)${NC}"
echo "---"
LOGIN_USER='{
  "username": "test_user",
  "password": "TestPass123"
}'
LOGIN_USER_RESPONSE=$(curl -s -X POST "$AUTH_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "$LOGIN_USER")
echo "$LOGIN_USER_RESPONSE" | jq '.'
USER_TOKEN=$(echo "$LOGIN_USER_RESPONSE" | jq -r '.data.access_token')
echo ""

# ==================== PRUEBA 5: GET Empleados (CON TOKEN ADMIN) ====================
echo -e "${BLUE}5. GET /empleados (CON TOKEN ADMIN)${NC}"
echo "---"
GET_EMPLEADOS=$(curl -s -X GET "$EMPLEADOS_URL/empleados" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
echo "$GET_EMPLEADOS" | jq '.'
echo ""

# ==================== PRUEBA 6: GET Empleados (CON TOKEN USER) ====================
echo -e "${BLUE}6. GET /empleados (CON TOKEN USER) - Debe funcionar (solo lectura)${NC}"
echo "---"
GET_EMPLEADOS_USER=$(curl -s -X GET "$EMPLEADOS_URL/empleados" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $USER_TOKEN")
echo "$GET_EMPLEADOS_USER" | jq '.'
echo ""

# ==================== PRUEBA 7: GET Empleados (SIN TOKEN) ====================
echo -e "${BLUE}7. GET /empleados (SIN TOKEN) - Debe devolver 401${NC}"
echo "---"
GET_EMPLEADOS_NO_TOKEN=$(curl -s -w "\nStatus: %{http_code}\n" -X GET "$EMPLEADOS_URL/empleados" \
    -H "Content-Type: application/json")
echo "$GET_EMPLEADOS_NO_TOKEN"
echo ""

# ==================== PRUEBA 8: POST Empleados (ADMIN) ====================
echo -e "${BLUE}8. POST /empleados (ADMIN) - Debe funcionar${NC}"
echo "---"
POST_EMPLEADO='{
  "nombre": "Carlos López",
  "departamento_id": "D001"
}'
POST_RESPONSE=$(curl -s -w "\nStatus: %{http_code}\n" -X POST "$EMPLEADOS_URL/empleados" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "$POST_EMPLEADO")
echo "$POST_RESPONSE"
echo ""

# ==================== PRUEBA 9: POST Empleados (USER) ====================
echo -e "${BLUE}9. POST /empleados (USER) - Debe devolver 403 Forbidden${NC}"
echo "---"
POST_USER=$(curl -s -w "\nStatus: %{http_code}\n" -X POST "$EMPLEADOS_URL/empleados" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $USER_TOKEN" \
    -d "$POST_EMPLEADO")
echo "$POST_USER"
echo ""

# ==================== PRUEBA 10: Validar Token ====================
echo -e "${BLUE}10. Validar Token JWT${NC}"
echo "---"
VALIDATE_TOKEN="{\"token\": \"$ADMIN_TOKEN\"}"
VALIDATE_RESPONSE=$(curl -s -X POST "$AUTH_URL/auth/validate" \
    -H "Content-Type: application/json" \
    -d "$VALIDATE_TOKEN")
echo "$VALIDATE_RESPONSE" | jq '.'
echo ""

# ==================== RESUMEN ====================
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Pruebas Completadas${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo "Tokens para referencia:"
echo -e "${YELLOW}ADMIN_TOKEN:${NC} ${ADMIN_TOKEN:0:50}..."
echo -e "${YELLOW}USER_TOKEN:${NC}  ${USER_TOKEN:0:50}..."
echo ""

echo "Próximos pasos:"
echo "1. ✓ Revisar los logs de los servicios"
echo "   docker-compose logs auth-service"
echo "   docker-compose logs empleados-service"
echo "   docker-compose logs notificaciones-service"
echo ""
echo "2. ✓ Probar en Swagger UI:"
echo "   http://localhost:8082/apidocs/"
echo ""
echo "3. ✓ Monitorear RabbitMQ:"
echo "   http://localhost:15672 (admin:admin)"
