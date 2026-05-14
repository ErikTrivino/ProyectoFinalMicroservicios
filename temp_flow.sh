#!/usr/bin/env bash
TOKEN=$(curl -s -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c 'import sys, json; print(json.load(sys.stdin)["data"]["access_token"])')
echo "TOKEN=$TOKEN"

curl -X POST http://localhost:8080/empleados \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"cedula":"E010","nombre":"Ana Gómez","email":"ana@empresa.com","departamentoId":"IT","fechaIngreso":"2026-05-20"}'

for i in {1..10}; do
  curl -s http://localhost:8080/empleados \
    -H "Authorization: Bearer $TOKEN" >/dev/null
  sleep 1
done

echo Done
