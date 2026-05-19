#!/bin/bash
# ============================================================
# wait-for-services.sh
# Script de health check polling para verificar que todos los
# servicios estén operativos antes de ejecutar pruebas E2E
# ============================================================

MAX_RETRIES=30
RETRY_INTERVAL=10

check_service() {
    local name=$1
    local url=$2
    local retries=0

    echo "⏳ Esperando a $name ($url)..."
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|401\|403"; then
            echo "✅ $name está operativo"
            return 0
        fi
        
        retries=$((retries + 1))
        echo "  Intento $retries/$MAX_RETRIES para $name..."
        sleep $RETRY_INTERVAL
    done
    
    echo "❌ $name no respondió después de $MAX_RETRIES intentos"
    return 1
}

echo "========================================"
echo "  Verificando servicios del sistema..."
echo "========================================"

FAILED=0

check_service "empleados-service" "http://empleados-service:80/health" || FAILED=1
check_service "auth-service" "http://auth-service:80/health" || FAILED=1
check_service "departamentos-service" "http://departamentos-service:8081/health" || FAILED=1
check_service "notificaciones-service" "http://notificaciones-service:8084/health" || FAILED=1
check_service "perfiles-service" "http://perfiles-service:8083/actuator/health" || FAILED=1

if [ $FAILED -eq 0 ]; then
    echo "========================================"
    echo "  ✅ Todos los servicios están listos"
    echo "========================================"
    exit 0
else
    echo "========================================"
    echo "  ❌ Algunos servicios no están listos"
    echo "========================================"
    exit 1
fi
