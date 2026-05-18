#!/usr/bin/env bash
set -e

TOKEN=$(curl -s -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c 'import sys,json; print(json.load(sys.stdin)["data"]["access_token"])')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "No se pudo obtener el token ADMIN. Revisa que auth-service este activo en http://localhost:8082"
  exit 1
fi

echo "Token ADMIN obtenido."
echo "TOKEN_USADO_COMPLETO=$TOKEN"
echo "TOKEN_USADO_CORTO=${TOKEN:0:25}..."

CEDULA="$(date +%s)${RANDOM}"
EMAIL="vac.${CEDULA}@empresa.com"
USER_PASSWORD="Vac12345!"
TRACE_ID="vac-trace-$(date +%s)"

echo "TRACE_ID=$TRACE_ID"

# Crear departamento base (idempotente)
curl -s -X POST http://localhost:8086/departamentos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"id":"IT","nombre":"Tecnologia","descripcion":"Departamento de TI"}' >/dev/null || true

# Crear empleado para asociarle vacaciones
curl -s -X POST http://localhost:8080/empleados \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"cedula\":\"$CEDULA\",\"nombre\":\"Ana Vacaciones\",\"email\":\"$EMAIL\",\"departamentoId\":\"IT\",\"fechaIngreso\":\"2026-05-20\",\"password\":\"$USER_PASSWORD\"}" >/dev/null

echo "Empleado creado: cedula=$CEDULA email=$EMAIL"

echo
echo "Esperando sincronizacion de usuario en auth-service..."
sleep 3

USER_TOKEN=$(curl -s -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$EMAIL\",\"password\":\"$USER_PASSWORD\"}" | python -c 'import sys,json; print(json.load(sys.stdin)["data"]["access_token"])')

if [ -z "$USER_TOKEN" ] || [ "$USER_TOKEN" = "null" ]; then
  echo "No se pudo obtener token del usuario creado ($EMAIL)."
  exit 1
fi

echo "Token USUARIO obtenido."
echo "TOKEN_USUARIO_CORTO=${USER_TOKEN:0:25}..."

echo
echo "Programando vacaciones..."
echo "Solicitud vacaciones => cedula=$CEDULA fecha_inicio=2026-06-10 fecha_fin=2026-06-15 token_usuario_corto=${USER_TOKEN:0:25}... trace_id=$TRACE_ID"
curl -s -X POST http://localhost:8085/vacaciones \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d "{\"cedula\":\"$CEDULA\",\"fecha_inicio\":\"2026-06-10\",\"fecha_fin\":\"2026-06-15\"}"

echo
echo "Consultando vacaciones por cedula..."
VACACIONES_JSON=$(curl -s -X GET "http://localhost:8085/vacaciones/$CEDULA" \
  -H "Authorization: Bearer $USER_TOKEN")
echo "$VACACIONES_JSON"

# Obtener el id entero de la solicitud de vacaciones mas reciente
VACACION_ID=$(echo "$VACACIONES_JSON" | python -c 'import sys,json; data=json.load(sys.stdin); print((data[0] or {}).get("id","") if isinstance(data,list) and data else "")')

if [ -z "$VACACION_ID" ] || [ "$VACACION_ID" = "null" ]; then
  echo "No se pudo obtener el id de vacaciones para cedula=$CEDULA"
  exit 1
fi

echo
echo "Solicitud creada. Cancelacion pendiente para ejecucion manual."
echo "Para cancelar manualmente usa:"
echo "curl -X PUT \"http://localhost:8085/vacaciones/$VACACION_ID/estado\" -H \"Authorization: Bearer $USER_TOKEN\" -H \"Content-Type: application/json\" -d '{\"estado\":\"Cancelada\"}'"

echo
echo "Prueba de vacaciones completada."
