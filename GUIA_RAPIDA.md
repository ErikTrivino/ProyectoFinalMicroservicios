# 🚀 Guía Rápida - Microservicios JWT

> Referencia rápida de cómo usar la API. Más detalles en `README.md` e `IMPLEMENTACION.md`

---

## 🎯 Inicio Rápido

### 1️⃣ Levantar servicios
```bash
docker-compose up -d
docker-compose ps  # Verificar que todos están "Up"
```

### 2️⃣ Abrir Swagger UI
```
http://localhost:8082/apidocs/
```

### 3️⃣ Registrar usuario
```http
POST http://localhost:8082/auth/register
Content-Type: application/json

{
  "username": "juan",
  "email": "juan@empresa.com",
  "password": "Pass123"
}
```

### 4️⃣ Login
```http
POST http://localhost:8082/auth/login
Content-Type: application/json

{
  "username": "juan",
  "password": "Pass123"
}
```

**Guardar:** `access_token` de la respuesta

### 5️⃣ Usar el token
```http
GET http://localhost:8080/empleados
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📌 Usuarios de Prueba (Ya Creados)

| Usuario | Password | Rol |
|---------|----------|-----|
| admin | admin123 | ADMIN |
| user | user123 | USER |

```bash
# Probar directamente:
curl -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

---

## 🔑 Endpoints - Auth Service (8082)

### POST `/auth/register`
Registrar nuevo usuario (role=USER)
```bash
curl -X POST http://localhost:8082/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "juan",
    "email": "juan@empresa.com",
    "password": "Pass123"
  }'
```

### POST `/auth/login`
Obtener JWT token
```bash
curl -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "juan",
    "password": "Pass123"
  }'

# Response:
# {
#   "access_token": "eyJhbGc...",
#   "token_type": "bearer",
#   "expires_in": 900,
#   "role": "USER"
# }
```

### POST `/auth/recover-password`
Solicitar recuperación de contraseña
```bash
curl -X POST http://localhost:8082/auth/recover-password \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@empresa.com"}'
```

### POST `/auth/reset-password`
Restablecer contraseña (recibir token en logs de notificaciones)
```bash
curl -X POST http://localhost:8082/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGc... (reset_token)",
    "newPassword": "NewPass456"
  }'
```

### POST `/auth/validate`
Validar un token
```bash
curl -X POST http://localhost:8082/auth/validate \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJhbGc..."}'
```

### GET `/health`
Health check
```bash
curl http://localhost:8082/health
```

---

## 📊 Endpoints - Empleados Service (8080) - Requieren JWT

### GET `/empleados`
Listar (ADMIN y USER pueden)
```bash
TOKEN="eyJhbGc..."
curl http://localhost:8080/empleados \
  -H "Authorization: Bearer $TOKEN"

# Sin token: 401 Unauthorized
```

### POST `/empleados`
Crear (Solo ADMIN)
```bash
TOKEN="eyJhbGc... (ADMIN token)"
curl -X POST http://localhost:8080/empleados \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Maria Garcia",
    "departamento_id": "D001"
  }'

# Con USER token: 403 Forbidden
```

### DELETE `/empleados/{id}`
Eliminar (Solo ADMIN)
```bash
TOKEN="eyJhbGc... (ADMIN token)"
curl -X DELETE http://localhost:8080/empleados/E001 \
  -H "Authorization: Bearer $TOKEN"

# Con USER token: 403 Forbidden
```

---

## 🛡️ Códigos de Error

| Código | Significado | Causa |
|--------|-------------|-------|
| **200** | OK | Request exitoso |
| **201** | Created | Recurso creado |
| **400** | Bad Request | Datos incompletos |
| **401** | Unauthorized | Token faltante, expirado o inválido |
| **403** | Forbidden | Rol sin permisos |
| **404** | Not Found | Recurso no existe |
| **409** | Conflict | Usuario/email duplicado |
| **500** | Server Error | Error interno |

---

## 🧪 Pruebas Rápidas

### Test 1: Health check
```bash
curl http://localhost:8082/health
# ✓ PASSED si returns 200
```

### Test 2: Login y obtener token
```bash
RESPONSE=$(curl -s -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo "$RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo "Token: $TOKEN"
```

### Test 3: Usar token (debe funcionar)
```bash
curl http://localhost:8080/empleados \
  -H "Authorization: Bearer $TOKEN"
# ✓ PASSED si returns 200 + lista
```

### Test 4: Sin token (debe fallar)
```bash
curl http://localhost:8080/empleados
# ✓ PASSED si returns 401
```

### Test 5: USER intenta escribir (debe fallar)
```bash
USER_TOKEN="..."
curl -X POST http://localhost:8080/empleados \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"nombre":"Test"}'
# ✓ PASSED si returns 403
```

---

## 📋 Estructura del Token JWT

```
TOKEN = <header>.<payload>.<signature>

Puedes decodificar en: https://jwt.io/

Ejemplo payload:
{
  "sub": "admin",              # username
  "role": "ADMIN",             # rol
  "type": "ACCESS",            # tipo de token
  "iat": 1775526332,           # created
  "exp": 1775529932            # expires (60 min)
}
```

---

## 🐳 Docker Compose

```bash
# Levantar
docker-compose up -d

# Ver logs
docker-compose logs -f auth-service
docker-compose logs -f notificaciones-service

# Health check
docker-compose ps

# Detener
docker-compose down

# Rebuild
docker-compose up -d --build
```

---

## 🔗 URLs Importantes

| Servicio | URL | Puerto |
|----------|-----|--------|
| Auth Service | http://localhost:8082 | 8082 |
| Auth Docs | http://localhost:8082/apidocs/ | 8082 |
| Empleados | http://localhost:8080 | 8080 |
| Departamentos | http://localhost:8081 | 8081 |
| Notificaciones | http://localhost:8084 | 8084 |
| RabbitMQ UI | http://localhost:15672 | 15672 |
| → user: admin, pass: admin |  |  |

---

## 🔑 Variables de Entorno

```bash
# docker-compose.yml
JWT_SECRET=supersecreto              # ← CAMBIAR EN PRODUCCIÓN
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=60      # 60 minutos
RESET_TOKEN_EXPIRES_MINUTES=60       # 60 minutos

# Usuarios seed
AUTH_ADMIN_USER=admin
AUTH_ADMIN_PASSWORD=admin123
AUTH_DEFAULT_USER=user
AUTH_DEFAULT_PASSWORD=user123
```

---

## 💡 Tips Útiles

### Guardar token en variable de entorno
```bash
# Linux/Mac
TOKEN=$(curl -s -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

export TOKEN
echo $TOKEN
```

### Usar Postman/Bruno
1. Importar `PRUEBAS.json`
2. Ejecutar "Login ADMIN"
3. Token se guarda automáticamente
4. Usar en otros requests

### Ver detalles del token
```bash
# En línea: https://jwt.io/
# O decodificar localmente:
echo $TOKEN | cut -d'.' -f2 | base64 -d | python -m json.tool
```

### Monitorear eventos RabbitMQ
```bash
docker-compose logs -f message-broker
docker-compose logs -f auth-service       # consume empleado.creado
docker-compose logs -f notificaciones-service  # consume usuario.creado
```

---

## ⚡ Flujo Rápido Completo

```bash
# 1. Levantar
docker-compose up -d

# 2. Esperar 5 segundos a que inicie
sleep 5

# 3. Login ADMIN
ADMIN=$(curl -s -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

ADMIN_TOKEN=$(echo $ADMIN | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# 4. Ver empleados
curl http://localhost:8080/empleados \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python -m json.tool

# 5. Crear empleado (genera eventos)
curl -X POST http://localhost:8080/empleados \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Test User","departamento_id":"D001"}'

# 6. Ver eventos
docker-compose logs auth-service | grep "usuario.creado"
docker-compose logs notificaciones-service | grep "SEGURIDAD"
```

---

## ❌ Errores Comunes

### Error: 401 Unauthorized
- ❌ Token no incluido en header
- ❌ Token expirado (>60 min)
- ❌ Formato incorrecto: debe ser `Authorization: Bearer <token>`
- ✅ Solución: Hacer login nuevamente

### Error: 403 Forbidden
- ❌ Usando USER token para operación que requiere ADMIN
- ✅ Solución: Usar ADMIN_TOKEN o cambiar rol del usuario

### Error: auth-service no conecta
- ❌ database-auth no está running
- ❌ RabbitMQ no está running
- ✅ Solución: `docker-compose restart`

### Error: JWT_SECRET mismatch
- ❌ Servicios tienen diferente JWT_SECRET
- ✅ Verificar docker-compose.yml todos tienen el mismo

---

## 📞 Soporte

- 📖 Documentación completa: `README.md`
- 📋 Implementación detallada: `IMPLEMENTACION.md`
- 🧪 Ejemplos de requests: `PRUEBAS.json`
- 🔗 API Docs: http://localhost:8082/apidocs/
- 💬 RabbitMQ Management: http://localhost:15672

---

**Última actualización:** Abril 2026  
**Versión:** 1.0 Quick Reference
