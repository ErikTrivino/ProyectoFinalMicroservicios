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

TRACE_ID="dep-trace-$(date +%s)"
echo "TRACE_ID=$TRACE_ID"
RUN_TS="$(date +%s)"

# Cantidad de departamentos a crear (por defecto: 20)
TOTAL="${1:-20}"

for i in $(seq 1 "$TOTAL"); do
  DEP_ID="DEP${RUN_TS}${i}"
  DEP_NOMBRE="Departamento_${RUN_TS}_$i"
  DEP_DESC="Departamento generado para metricas $i"

  RESP=$(curl -s -X POST http://localhost:8086/departamentos \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"id\":\"$DEP_ID\",\"nombre\":\"$DEP_NOMBRE\",\"descripcion\":\"$DEP_DESC\"}")

  echo "[$i/$TOTAL] Creado: id=$DEP_ID nombre=$DEP_NOMBRE"
  echo "$RESP" >/dev/null
  sleep 0.2
done

echo
echo "Generando lecturas para metricas..."
for i in $(seq 1 "$TOTAL"); do
  curl -s http://localhost:8086/departamentos \
    -H "Authorization: Bearer $TOKEN" >/dev/null
done

echo "Prueba de departamentos completada. Departamentos intentados: $TOTAL"
