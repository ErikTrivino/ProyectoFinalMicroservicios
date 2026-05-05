# Microservicios de Gestión de Empleados con Autenticación JWT

> Arquitectura de microservicios que implementa autenticación centralizada con JWT, autorización basada en roles (RBAC) y eventos de ciclo de vida para empleados.

**Equipo:** Erik Pablo Triviño Gonzalez | Felipe Valencia Londoño | Anderson Betancurt | Jose Felipe Gabinos

---

## 📋 Tabla de Contenidos

1. [Arquitectura](#arquitectura)
2. [Flujo de Autenticación](#flujo-de-autenticación)
3. [Seguridad JWT](#seguridad-jwt)
4. [Roles y Permisos](#roles-y-permisos)
5. [Instalación](#instalación)
6. [Uso de la API](#uso-de-la-api)
7. [Ejemplos de Requests](#ejemplos-de-requests)
8. [Pruebas Completas](#pruebas-completas)
9. [Solución de Problemas](#solución-de-problemas)
10. [Integración Continua (CI)](#-integración-continua-ci--reto-6)


---

## Arquitectura

### Componentes

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **auth-service** | 8082 | Proveedor central de identidad. Emite JWT y valida credenciales |
| **empleados-service** | 8080 | CRUD de empleados. Requiere JWT en Authorization header |
| **departamentos-service** | 8081 | CRUD de departamentos. Requiere JWT |
| **notificaciones-service** | 3000 | Consumer de eventos. Registra notificaciones de ciclo de vida |
| **perfiles-service** | 8083 | Gestión de perfiles de empleados (Java/Spring Boot) |
| **RabbitMQ** | 5672 | Message broker para eventos asíncronos |
| **PostgreSQL (x4)** | N/A | Bases de datos independientes por servicio |
| **Jenkins** | 9090 | Servidor de Integración Continua (Reto 6) |
| **SonarQube** | 9000 | Análisis de calidad de código (Reto 6) |
| **Docker Registry** | 5000 | Registry local para imágenes Docker (Reto 6) |

### Flujo de Eventos

```
[POST /empleados] 
    ↓ (ADMIN crea empleado)
[empleados_events exchange - empleado.creado]
    ↓ (evento publicado)
[auth-service consume]
    ↓ (crea user con email del empleado)
[usuario_events exchange - usuario.creado]
    ↓ (con reset_token en evento)
[notificaciones-service consume]
    ↓ (registra notificación con token)
```

---

## Flujo de Autenticación

### 1️⃣ Login

```http
POST /auth/login HTTP/1.1
Host: localhost:8082
Content-Type: application/json

{
  "username": "juan_perez",
  "password": "miPassword123"
}
```

**Respuesta 200:**
```json
{
  "success": true,
  "message": "Autenticación correcta",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 900,
    "role": "USER"
  }
}
```

### 3️⃣ Usar Token

En el header de **CUALQUIER request protegido:**

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 4️⃣ Recuperar Contraseña

```http
POST /auth/recover-password HTTP/1.1
Host: localhost:8082
Content-Type: application/json

{
  "email": "juan@empresa.com"
}
```

Luego recibir el reset_token en notificaciones y usar:

```http
POST /auth/reset-password HTTP/1.1
Host: localhost:8082
Content-Type: application/json

{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "newPassword": "nuevaPassword456"
}
```

---

## Seguridad JWT

### Características

| Aspecto | Implementación |
|--------|-----------------|
| **Algoritmo** | HS256 (Simétrico) |
| **Expiración** | 60 minutos (ACCESS), 60 minutos (RESET) |
| **Hash** | bcrypt con salt |
| **Almacenamiento** | Variable de entorno `JWT_SECRET` |

### Estructura del Token

```
Header:
{
  "alg": "HS256",
  "typ": "JWT"
}

Payload:
{
  "sub": "usuario",
  "role": "ADMIN",
  "type": "ACCESS",
  "iat": 1704067200,
  "exp": 1704068100
}

Signature: HMACSHA256(header.payload, JWT_SECRET)
```

### Validación en Servicios

1. ✅ Cliente envía: `Authorization: Bearer <token>`
2. ✅ Servicio verifica firma con `JWT_SECRET` compartido
3. ✅ Si expirado o alterado: **401 Unauthorized**
4. ✅ Si sin permisos para la acción: **403 Forbidden**

---

## Roles y Permisos (RBAC)

### ADMIN ✅ Acceso Total

| Recurso | GET | POST | DELETE |
|---------|-----|------|--------|
| `/empleados` | ✅ | ✅ | ✅ |
| `/departamentos` | ✅ | ✅ | ✅ |

### USER 🔍 Solo Lectura

| Recurso | GET | POST | DELETE |
|---------|-----|------|--------|
| `/empleados` | ✅ | ❌ 403 | ❌ 403 |
| `/departamentos` | ✅ | ❌ 403 | ❌ 403 |

---

## Instalación

### Prerrequisitos
- Docker y Docker Compose
- Git

### Pasos

```bash
# 1. Clonar
git clone <repo>
cd ProyectoFinalMicroservicios

# 2. Levantar servicios
docker-compose up -d

# 3. Verificar
docker-compose ps

# 4. Ver logs
docker-compose logs -f auth-service
```

### Variables de Entorno (docker-compose.yml)

```yaml
environment:
  JWT_SECRET: "supersecreto"
  JWT_ALGORITHM: "HS256"
  ACCESS_TOKEN_EXPIRES_MINUTES: 60
  RESET_TOKEN_EXPIRES_MINUTES: 60
  RABBITMQ_URL: "amqp://admin:admin@message-broker:5672"
```

⚠️ **En producción:** Cambiar `JWT_SECRET` a un valor seguro y único.

---

## Uso de la API

### 🎯 Swagger UI

```
http://localhost:8082/apidocs/
```

✅ Registrate | ✅ Login | ✅ Copia token | ✅ Prueba endpoints

### Endpoints Principales

#### POST `/auth/login` - Login
```bash
curl -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "juan",
    "password": "Pass123"
  }'
# Respuesta: { "access_token": "...", "role": "USER" }
```

#### POST `/auth/recover-password` - Recuperar
```bash
curl -X POST http://localhost:8082/auth/recover-password \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@empresa.com"}'
```

#### POST `/auth/reset-password` - Restablecer
```bash
curl -X POST http://localhost:8082/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "reset_token_here",
    "newPassword": "NewPass456"
  }'
```

### Endpoints Protegidos (empleados-service)

#### GET `/empleados` - Requiere JWT
```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
curl -X GET http://localhost:8080/empleados \
  -H "Authorization: Bearer $TOKEN"
```

#### POST `/empleados` - Solo ADMIN
```bash
curl -X POST http://localhost:8080/empleados \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Maria Garcia",
    "departamento_id": "D001"
  }'
```

#### DELETE `/empleados/{id}` - Solo ADMIN
```bash
curl -X DELETE http://localhost:8080/empleados/E001 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Ejemplos de Requests

### Usuarios por Defecto

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `admin` | `admin123` | ADMIN |
| `user` | `user123` | USER |

### Flujo Completo

```bash
# 1️⃣ Login
RESPONSE=$(curl -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"maria","password":"MyPass123"}')

TOKEN=$(echo $RESPONSE | jq -r '.data.access_token')

# 2️⃣ Usar token
curl -X GET http://localhost:8080/empleados \
  -H "Authorization: Bearer $TOKEN"

# 3️⃣ Intentar operación no autorizada (debe fallar con 403)
curl -X POST http://localhost:8080/empleados \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Test","departamento_id":"D001"}'
```

---

## Pruebas Completas

### Checklist

- [ ] Paso 1: Registrar usuario USER
- [ ] Paso 2: Login con USER
- [ ] Paso 3: GET `/empleados` con TOKEN → 200 OK
- [ ] Paso 4: GET `/empleados` SIN token → 401 Unauthorized
- [ ] Paso 5: DELETE `/empleados/{id}` con USER token → 403 Forbidden
- [ ] Paso 6: DELETE `/empleados/{id}` con ADMIN token → 200 OK
- [ ] Paso 7: Recuperar contraseña → Recibir token en logs
- [ ] Paso 8: Restablecer contraseña con token
- [ ] Paso 9: Verificar eventos en `docker-compose logs`

### Verificar Eventos

```bash
# Ver logs de auth-service
docker-compose logs auth-service | grep "usuario.creado"

# Ver logs de notificaciones
docker-compose logs notificaciones-service | grep "SEGURIDAD"
```

---

## Solución de Problemas

### ❌ "401 Unauthorized" en todo

**Solución:**
```bash
# Verificar que incluyes: Authorization: Bearer <TOKEN>
# Verificar que el token no está expirado (>60 min)
# Hacer login nuevamente
```

### ❌ "403 Forbidden" en POST/DELETE

**Solución:**
```bash
# Usar token de ADMIN, no USER
# USER solo puede hacer GET
```

### ❌ auth-service no conecta a BD

**Solución:**
```bash
docker-compose restart
docker-compose logs database-auth
```

### ❌ Eventos no se propagan

**Solución:**
```bash
docker-compose logs message-broker
# Acceder a: http://localhost:15672 (admin:admin)
```

---

## 📊 Criterios de Evaluación

| Criterio | Estado | Detalles |
|----------|--------|----------|
| **Autenticación JWT** | ✅ | auth-service emite tokens, bcrypt hashing |
| **Validación de Token** | ✅ | 401 para tokens inválidos/expirados |
| **RBAC** | ✅ | ADMIN acceso total, USER solo lectura, 403 denegación |
| **Variables de Entorno** | ✅ | JWT_SECRET en docker-compose, no hardcodeado |
| **Documentación** | ✅ | OpenAPI/Swagger, README con ejemplos, cURL |

---

## 🔐 Protección de Microservicios - Resumen

### Estrategia Implementada: **Middleware/Interceptor por Servicio**

✅ **Ventajas:**
- Cada servicio es independiente
- No hay punto único de fallo
- Escalable horizontalmente
- Rápido de implementar

### Flujo de Validación

```
[Request + Bearer Token]
    ↓
[Decorador @validar_token()]
    ↓
[Verifica firma JWT con JWT_SECRET]
    ↓
[401 si inválido/expirado]
    ↓
[Decodifica role del payload]
    ↓
[Decorador @requerir_rol('ADMIN', 'USER')]
    ↓
[403 si rol sin permisos]
    ↓
[Procesa request]
```

---

## 🔄 Integración Continua (CI) — Reto 6

### ¿Qué es CI y por qué se integra?

La **Integración Continua (CI)** automatiza la compilación, pruebas y empaquetado del código en cada cambio. En este proyecto de microservicios es especialmente valiosa porque:

- **Múltiples servicios, múltiples lenguajes:** Python, Java, C# — cada uno con su propio pipeline
- **Detección temprana de errores:** Los problemas se detectan en minutos, no en días
- **Deployments independientes:** Cada servicio se compila, prueba y empaqueta de forma independiente
- **Confianza en el código:** El pipeline verifica todo en un entorno limpio y reproducible

### 🏗️ Arquitectura CI

```
🐳 Docker Compose
├── ⚙️ Jenkins (:9090)         → Servidor CI
├── 🔍 SonarQube (:9000)       → Calidad de código
├── 🗄️ Docker Registry (:5000) → Registry local de imágenes
└── [microservicios existentes...]
```

### 🔗 Acceso a Servicios CI

| Servicio | URL | Credenciales |
|----------|-----|-------------|
| **Jenkins** | http://localhost:9090 | `admin` / `admin123` |
| **SonarQube** | http://localhost:9000 | `admin` / `admin` (cambiar en 1er login) |
| **Docker Registry** | http://localhost:5000 | Sin autenticación |

### 📋 Instrucciones de Configuración

#### a. Levantar el sistema con Jenkins incluido

```bash
docker-compose up --build -d
```

Esto levanta todos los microservicios + Jenkins + SonarQube + Docker Registry.

#### b. Obtener acceso a Jenkins

Jenkins se configura automáticamente sin Setup Wizard. Acceder a http://localhost:9090 con `admin` / `admin123`.

#### c. Crear/importar los pipelines

Los pipelines se aprovisionan automáticamente via **JCasC** (Jenkins Configuration as Code). Al levantar Jenkins, los jobs ya están creados:
- `empleados-service-pipeline` (Python/Flask)
- `perfiles-service-pipeline` (Java/Spring Boot)
- `verificacion-docker` (Pipeline de verificación)

#### d. Ejecutar un pipeline manualmente

1. Ir al job en Jenkins (ej. `empleados-service-pipeline`)
2. Click en **"Build Now"**
3. Observar progreso en **"Stage View"**
4. Click en cada etapa para ver logs detallados

### ⚙️ Etapas del Pipeline

| # | Etapa | Qué verifica | ✅ Verde | ❌ Rojo |
|---|-------|-------------|---------|--------|
| 1 | **Checkout** | Obtiene código fuente | Código descargado | Repo no accesible |
| 2 | **Build** | Compila/instala dependencias | Compilación exitosa | Error de compilación |
| 3 | **Test** | Tests unitarios + cobertura | Todos los tests pasan | Un test falla |
| 4 | **SonarQube** | Envía análisis de calidad | Análisis completado | SonarQube no disponible |
| 5 | **Quality Gate** | Verifica cobertura ≥ 70% | Cumple umbrales | Cobertura insuficiente |
| 6 | **Package** | Construye imagen Docker | Imagen construida | Error en Dockerfile |
| 7 | **Publish** | Publica imagen al registry | Push exitoso | Registry no disponible |
| 8 | **E2E Tests** | Pruebas funcionales BDD | Escenarios pasan | Escenario falla |

### 📊 Cómo interpretar los resultados

- **Todo verde:** El código compila, pasa tests, cumple calidad y las pruebas E2E son exitosas
- **Rojo en Test:** Hay un test unitario que falla — revisar el log de la etapa
- **Rojo en Quality Gate:** La cobertura está por debajo del 70% — agregar más tests
- **Rojo en Package:** Error en el Dockerfile — verificar la sintaxis
- **Rojo en E2E:** Un escenario BDD falla — verificar los endpoints del servicio

> 📖 **Documentación detallada:** Ver [RETO6_CI.md](RETO6_CI.md) para decisiones técnicas, justificaciones y configuración avanzada.

### 🔧 Configuración de SonarQube

1. Acceder a http://localhost:9000 y cambiar contraseña
2. Crear token: **My Account → Security → Generate Token**
3. Actualizar token en `jenkins/casc.yaml`
4. Crear Quality Gate personalizado con cobertura ≥ 70%
5. Configurar webhook: **Administration → Webhooks → Create** → `http://jenkins:8080/sonarqube-webhook/`

---

## 📚 Información de Contacto

- 📧 Email: [tu-email@empresa.com]
- 🔗 API Docs: `http://localhost:8082/apidocs/`
- 📡 RabbitMQ Management: `http://localhost:15672` (admin:admin)
- ⚙️ Jenkins CI: `http://localhost:9090` (admin:admin123)
- 🔍 SonarQube: `http://localhost:9000` (admin:admin)

**Version:** 2.0.0 | **Last Updated:** Mayo 2026
