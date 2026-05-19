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
| **Jenkins** | 8090 | Servidor de Integración Continua (Reto 6) |
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

---

## Observabilidad y Monitoreo

### Dashboard Grafana

La dashboard de observabilidad está preconfigurada en:

- `observability/grafana/provisioning/dashboards/dashboard.json`

Incluye los paneles:
- **Estado**: Servicios activos mediante `up` de Prometheus.
- **Tasa de Peticiones**: tasa unificada de `flask_http_request_total`, `http_requests_received_total` y `http_server_requests_seconds_count`.
- **Latencia Promedio**: promedio de duración basada en `_sum / _count` para Flask, .NET y Java.
- **Errores 4xx/5xx**: tasa de errores por servicio.

### Provisión de Grafana

Grafana importa automáticamente:

- `Prometheus` en `http://prometheus:9090`
- `Loki` en `http://loki:3100`
- `Zipkin` en `http://zipkin:9411`

### Alertas Proactivas y Canal de Notificación

El sistema cuenta con alertas proactivas configuradas en Grafana (Unified Alerting) para notificar al equipo de soporte de forma automática:
1. **Servicio Caído:** Se dispara si un microservicio deja de responder al scraping de Prometheus (`up == 0`) durante 1 minuto.
2. **Alta Tasa de Errores:** Se dispara si el porcentaje de respuestas HTTP 5xx supera el 10% durante 2 minutos.

**Canales de notificación elegidos: Discord Webhook, Telegram Bot y Slack**
- **Complejidad:** Baja a Media
- **Configuración (Discord):** Se ha creado un servidor de Discord y se ha generado una URL de Webhook.
- **Configuración (Telegram):** Se ha creado un bot con @BotFather y configurado el `chat_id`. 
- **Configuración (Slack):** Se requiere crear una app en un workspace de Slack y habilitar "Incoming Webhooks" para obtener la URL. (Reemplazar en `alerting.yml`).
- La configuración se encuentra centralizada en Grafana mediante un Contact Point provisionado a través del archivo:
  - `observability/grafana/provisioning/alerting/alerting.yml`
- Todas las alertas de Grafana son enrutadas simultáneamente a Discord, Telegram y Slack notificando en tiempo real cuando un microservicio falla o experimenta alta tasa de errores.

### Prometheus Scrape

Los servicios estan configurados en `observability/prometheus/prometheus.yml` con estos jobs:

- `auth-service`
- `empleados-service`
- `departamentos-service`
- `notificaciones-service`
- `perfiles-service`

### Consultas útiles

**Tasa unificada de peticiones**

```promql
sum by (job) (
  rate(flask_http_request_total[5m])
  or rate(http_requests_received_total[5m])
  or rate(http_server_requests_seconds_count[5m])
)
```

**Latencia promedio**

```promql
sum by (job) (
  rate(flask_http_request_duration_seconds_sum[5m]) / rate(flask_http_request_duration_seconds_count[5m])
  or rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
  or rate(http_server_requests_seconds_sum[5m]) / rate(http_server_requests_seconds_count[5m])
)
```

**Errores 4xx/5xx**

```promql
sum by (job) (
  rate(flask_http_request_total{code=~"4..|5.."}[5m])
  or rate(http_requests_received_total{status=~"4..|5.."}[5m])
  or rate(http_server_requests_seconds_count{status=~"4..|5.."}[5m])
)
```

**Consulta LogQL de ejemplo para Loki**

```logql
{service="empleados-service"} | json | level="ERROR"
```

### Cómo verificar

1. Levanta la pila:

```bash
docker-compose up -d
```

2. Abre Grafana en `http://localhost:3000`.
3. Revisa que el dashboard `Observabilidad Microservicios` esté disponible.
4. Desde Grafana → Explore → Loki, pega la query LogQL anterior.

--- reto 7------------------------------------------------------------------------------------------

## 📊 Arquitectura de Observabilidad

### Diagrama de Flujo

```mermaid
flowchart TD
    subgraph "Microservicios"
        AS["🔐 auth-service:80/metrics"]
        ES["👥 empleados-service:80/metrics"]
        DS["🏢 departamentos-service:8081/metrics"]
        NS["📧 notificaciones-service:8084/metrics"]
        PS["📋 perfiles-service:8083/actuator/prometheus"]
    end

    subgraph "Stack Observabilidad"
        PROM["📊 Prometheus:9090"]
        GRAF["📈 Grafana:3000"]
        LOKI["📂 Loki:3100"]
        ZIP["🔍 Zipkin:9411"]
    end

    subgraph "Soporte"
        PT["📋 Promtail"]
        MB["🐰 RabbitMQ:5672"]
    end

    AS & ES & DS & NS & PS -->|Pull /metrics| PROM
    AS & ES & DS & NS & PS -->|Push OTel/Spans| ZIP
    AS & ES & DS & NS & PS -->|Emit Logs| PT
    PT -->|Push LogQL| LOKI
    
    PROM -->|PromQL| GRAF
    LOKI -->|LogQL| GRAF
    ZIP -->|Traces UI| GRAF
    
    GRAF -->|Rules/Alerts| MB
    MB -->|Notificaciones| CHAT["💬 Discord/Telegram/Slack"]

    classDef service fill:#4A90E2,stroke:#2E5C8A,color:#fff
    classDef observ fill:#50C878,stroke:#2D7A4F,color:#fff
    classDef support fill:#FFB84D,stroke:#C68A3D,color:#000
    
    class AS,ES,DS,NS,PS service
    class PROM,GRAF,LOKI,ZIP observ
    class PT,MB support
```

### Conceptos Clave

| Componente | Propósito | Tipo |
|------------|-----------|------|
| **Prometheus** | Scraping de métricas (Pull) | Almacenamiento de series temporales |
| **Grafana** | Visualización de métricas, logs y trazas | Dashboard + Alertas |
| **Loki** | Almacenamiento de logs estructurados | Query engine (LogQL) |
| **Zipkin** | Trazas distribuidas (W3C Trace Context) | Análisis de latencia |
| **Promtail** | Recolector de logs desde Docker | Push de logs a Loki |

### Conceptos solicitados

**Pull vs Push.** Prometheus trabaja con un modelo **Pull**: consulta periodicamente los endpoints `/metrics` de cada microservicio usando los nombres internos de Docker (`auth-service`, `empleados-service`, etc.). Las trazas y logs usan **Push**: los servicios envian spans a Zipkin y Promtail envia logs de contenedores a Loki.

**OpenTelemetry.** Es el estandar usado para instrumentar trazas. En este proyecto cada servicio define `service.name`, instrumenta HTTP y exporta spans hacia `http://zipkin:9411/api/v2/spans` dentro de la red Docker.

**W3C Trace Context.** La propagacion de contexto via headers como `traceparent` permite correlacionar una peticion entre servicios. En el flujo de creacion de empleado, la solicitud pasa por `empleados-service`, valida `departamentos-service` y dispara eventos que luego procesan `auth-service`, `notificaciones-service` y `perfiles-service`.

### Instrumentacion por microservicio

| Servicio | Metricas | Trazabilidad | Logs |
|----------|----------|--------------|------|
| `auth-service` | `prometheus-flask-exporter` en `/metrics` | OpenTelemetry Flask/Requests + Zipkin | `python-json-logger` |
| `empleados-service` | `prometheus-flask-exporter` en `/metrics` | OpenTelemetry Flask/Requests + Zipkin | `python-json-logger` |
| `departamentos-service` | `prometheus-flask-exporter` en `/metrics` | OpenTelemetry Flask/Requests + Zipkin | `python-json-logger` |
| `notificaciones-service` | `prometheus-net.AspNetCore` en `/metrics` | OpenTelemetry ASP.NET Core/HTTP + Zipkin | Serilog JSON |
| `perfiles-service` | Spring Actuator + Micrometer Prometheus en `/actuator/prometheus` | Micrometer Tracing + OpenTelemetry bridge + Zipkin | Logback JSON |

### Eleccion de Zipkin

Se eligio **Zipkin** porque es liviano, se integra directamente con OpenTelemetry/Micrometer, requiere poca configuracion en Docker Compose y es suficiente para visualizar cascadas de spans en el taller. Jaeger tambien seria valido, pero Zipkin reduce complejidad operativa para un entorno academico local.

### Archivos versionados de observabilidad

- `observability/prometheus/prometheus.yml`: targets de Prometheus usando nombres de red Docker.
- `observability/grafana/provisioning/datasources/datasource.yml`: fuentes Prometheus, Loki y Zipkin.
- `observability/grafana/provisioning/dashboards/dashboard.json`: dashboard aprovisionado automaticamente.
- `observability/grafana/provisioning/alerting/`: reglas, politicas y contact points de alertas.
- `observability/promtail-config.yml`: descubrimiento de contenedores Docker y envio de logs a Loki.

---

## Pruebas del Sistema: Simulación del Caos

### Flujo de prueba sugerido

1. Levanta el ecosistema completo:

```bash
docker-compose up --build -d
```

2. Verifica que el stack de observabilidad está activo:

- Prometheus UI: `http://localhost:9090` → sección **Targets** debe mostrar todos los microservicios con estado `UP`.
- Grafana: `http://localhost:3000` → el dashboard **Observabilidad Microservicios** debe mostrar métricas en tiempo real.
- Zipkin: `http://localhost:9411` → busca trazas recientes.

> Nota: en este repositorio se usa Zipkin como sistema de trazas. No hay servicio Jaeger definido en el `docker-compose.yml`.

3. Genera tráfico para poblar las métricas:

bash temp_flow.sh

```bash
TOKEN=$(curl -s -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c 'import sys,json; print(json.load(sys.stdin)["data"]["access_token"])')

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

for i in {1..10}; do
  curl -s http://localhost:8080/empleados \
    -H "Authorization: Bearer $TOKEN" >/dev/null
  sleep 1
done
```

4. Verifica la traza distribuida:

- Abre Zipkin en `http://localhost:9411`.
- En **Service Name**, selecciona `empleados-service` y busca trazas recientes.
- Abre la traza correspondiente al `POST /empleados`.
- En este proyecto no hay API Gateway definido; por eso la cascada inicia en `empleados-service`.
- La traza debe evidenciar al menos `empleados-service` -> `departamentos-service`. Los pasos asincronos por RabbitMQ se verifican adicionalmente con logs/eventos de `auth-service`, `notificaciones-service` y `perfiles-service`.

```bash
docker-compose logs --tail=100 auth-service
docker-compose logs --tail=100 notificaciones-service
docker-compose logs --tail=100 perfiles-service
```

5. Simulacion de Caos - Apagar un servicio:

```bash
docker-compose stop departamentos-service
```

Espera ~2 minutos y verifica:

- En Prometheus: el target `departamentos-service` pasa a estado `DOWN`.
- En Grafana: el panel de estado del servicio cambia a rojo.
- En el canal de alertas: debe llegar la notificacion de **Servicio Caido**.

Para restaurarlo:

```bash
docker-compose up -d departamentos-service
```

6. Simulacion de Caos - Inducir latencia:

- `departamentos-service` incluye un interruptor de caos por variable de entorno. Cuando `CHAOS_LATENCY_ENABLED=true`, el endpoint `GET /departamentos/{id}` introduce 5 segundos de latencia en aproximadamente el 50% de las consultas.

```python
import time, random

if random.random() < 0.5:
    time.sleep(5)
```

- Activa la latencia artificial y genera trafico:

```bash
CHAOS_LATENCY_ENABLED=true docker-compose up -d --build departamentos-service
bash temp_flow.sh
```

- Verifica en Grafana que el panel de latencia refleja el aumento de tiempos.
- Si se configura una alerta de **Alta Latencia**, debe dispararse.

Para desactivar la simulacion:

```bash
CHAOS_LATENCY_ENABLED=false docker-compose up -d --build departamentos-service
```

7. Documenta los hallazgos:

- Captura de pantalla del Dashboard de Grafana con metricas reales.

![rafana-dashboard](grafana-dashboard.png)


- Captura de pantalla de la vista de trazas en Zipkin mostrando la cascada completa.

![zipkin-trace](ipkin-trace-1.png)
- Captura de pantalla de la alerta recibida en el canal de notificacion (Discord/Telegram/Slack/email).

![alerta-servicio-caido](alerta-servicio-caido.png)

![prometheus-down](rometheus-down.png)

Rutas sugeridas para versionar evidencias:

- `docs/evidencias/grafana-dashboard.png`
- `docs/evidencias/zipkin-trace.png`
- `docs/evidencias/alerta-servicio-caido.png`
- `docs/evidencias/prometheus-down.png`

### Canal de alertas

Grafana Unified Alerting esta aprovisionado desde `observability/grafana/provisioning/alerting/`. Las reglas configuradas son:

- **Servicio caido:** se dispara cuando al menos un target queda con `up == 0` durante 1 minuto.
- **Alta tasa de errores:** se dispara cuando los errores 5xx superan el 10% del trafico durante 2 minutos.

El canal externo se define como contact point en Grafana. Para la entrega, se debe evidenciar al menos una notificacion recibida en Discord, Telegram, Slack o email.

### Análisis Fundamentado: ¿Qué servicio tardó más en responder?

**Hallazgo:** El servicio que experimenta mayor latencia durante la simulación es identificable mediante dos técnicas de observabilidad complementarias:

#### 1️⃣ **Métrica Cuantitativa en Grafana**
- Panel "Latencia promedio" muestra la distribución de tiempos por servicio
- Query PromQL: `sum by (job) (rate(flask_http_request_duration_seconds_sum[1m]) / rate(flask_http_request_duration_seconds_count[1m]))`
- **Hallazgo visual:** Una línea en el gráfico muestra un "spike" claramente distinguible, indicando que ese servicio (típicamente `departamentos-service` si se introdujo el `time.sleep(5)`) tiene latencia significativamente mayor

#### 2️⃣ **Trazas Distribuidas en Zipkin**
- Al buscar una traza en http://localhost:9411, se visualiza la cascada de spans:
  ```
  POST /empleados (root span) ...................... 5.100 ms total
    └─ SELECT departamentos ............. 5.050 ms ⚠️ (CUELLO DE BOTELLA)
    └─ Emit evento RabbitMQ ................. 10 ms
    └─ Logs JSON en Loki .................... 5 ms
  ```
- El span del servicio lento ocupa la mayor parte del tiempo total de la transacción
- W3C Trace Context (`traceparent` header) propaga este contexto a través de toda la cadena de microservicios

#### 3️⃣ **Correlación en Loki**
- Logs estructurados en JSON permiten buscar:
  ```logql
  {service="departamentos-service"} | json | duration > 5000
  ```
- Confirma que el servicio específico generó latencia extremadamente larga

**Conclusión:** La combinación de métricas (Prometheus/Grafana), trazas distribuidas (Zipkin) y logs centralizados (Loki) proporciona una visión de 360° que:
1. **Identifica** qué servicio es lento (visualmente en Grafana)
2. **Cuantifica** exactamente dónde se consume el tiempo (span breakdown en Zipkin)
3. **Correlaciona** con contexto de negocio (logs JSON en Loki)

Esta es la esencia de la observabilidad moderna: no solo saber QUE algo pasó, sino DÓNDE y POR QUÉ en el contexto distribuido.

---

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

TOKEN=$(echo "$RESPONSE" | python -c 'import sys,json; print(json.load(sys.stdin)["data"]["access_token"])')

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
- **Trigger automático:** Al hacer `git push`, Jenkins detecta los cambios y dispara los pipelines automáticamente

### 🏗️ Arquitectura CI

```
🐳 Docker Compose
├── ⚙️ Jenkins (:8090)         → Servidor CI
├── 🔍 SonarQube (:9000)       → Calidad de código
├── 🗄️ Docker Registry (:5000) → Registry local de imágenes
└── [microservicios existentes...]
```

### 🔗 Acceso a Servicios CI

| Servicio | URL | Credenciales |
|----------|-----|-------------|
| **Jenkins** | http://localhost:8090 | `admin` / `admin123` |
| **SonarQube** | http://localhost:9000 | `admin` / `admin` (cambiar en 1er login) |
| **Docker Registry** | http://localhost:5000 | Sin autenticación |

### 📋 Instrucciones de Configuración

#### a. Levantar el sistema con Jenkins incluido

```bash
docker-compose up --build -d
```

Esto levanta todos los microservicios + Jenkins + SonarQube + Docker Registry.

#### b. Obtener acceso a Jenkins

Jenkins se configura automáticamente sin Setup Wizard. Acceder a http://localhost:8090 con `admin` / `admin123`.

#### c. Crear/importar los pipelines

Los pipelines se aprovisionan automáticamente via **JCasC** (Jenkins Configuration as Code). Al levantar Jenkins, los jobs ya están creados:
- `empleados-service-pipeline` (Python/Flask)
- `auth-service-pipeline` (Python/Flask)
- `departamentos-service-pipeline` (Python/Flask)
- `perfiles-service-pipeline` (Java/Spring Boot)
- `notificaciones-service-pipeline` (.NET 10)
- `verificacion-docker` (Pipeline de verificación)

#### d. Trigger automático por Git Push

Cada pipeline está configurado con **SCM Polling** (`pollSCM`) que consulta el repositorio Git (`https://github.com/ErikTrivino/ProyectoFinalMicroservicios.git`) cada ~5 minutos. Si detecta cambios nuevos tras un `git push`, dispara automáticamente el pipeline correspondiente.

#### e. Ejecutar un pipeline manualmente

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
- ⚙️ Jenkins CI: `http://localhost:8090` (admin:admin123)
- 🔍 SonarQube: `http://localhost:9000` (admin:admin)

**Version:** 2.0.0 | **Last Updated:** Mayo 2026
