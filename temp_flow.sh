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

CEDULA="E$(date +%s)"
EMAIL="ana.${CEDULA}@empresa.com"

curl -s -X POST http://localhost:8086/departamentos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"id":"IT","nombre":"Tecnologia","descripcion":"Departamento de TI"}' >/dev/null

curl -s -X POST http://localhost:8080/empleados \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"cedula\":\"$CEDULA\",\"nombre\":\"Ana Gomez\",\"email\":\"$EMAIL\",\"departamentoId\":\"IT\",\"fechaIngreso\":\"2026-05-20\"}"

echo
echo "Empleado solicitado: cedula=$CEDULA email=$EMAIL"

for i in {1..10}; do
  curl -s http://localhost:8080/empleados \
    -H "Authorization: Bearer $TOKEN" >/dev/null
  sleep 1
done

echo "Trafico generado para metricas y trazas."
