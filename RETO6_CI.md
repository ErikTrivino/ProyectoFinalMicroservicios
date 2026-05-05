# Reto 6 – Integración Continua con Jenkins

## Descripción General

Este reto implementa un pipeline de **Integración Continua (CI)** utilizando **Jenkins** dentro del ecosistema Docker del proyecto de microservicios de gestión de empleados. Cada microservicio cuenta con un `Jenkinsfile` que define un pipeline automatizado con las etapas de build, test, calidad, empaquetado Docker y pruebas E2E.

---

## ¿Qué es la Integración Continua?

La **Integración Continua (CI)** es una práctica de desarrollo de software en la que los desarrolladores integran su código en un repositorio compartido de forma frecuente, y cada integración se verifica automáticamente mediante compilación y pruebas.

| Aspecto | Sin CI | Con CI |
|---------|--------|--------|
| **Compilación** | Manual, cuando alguien se acuerda | Automática, en cada push |
| **Pruebas** | Se ejecutan localmente (o no se ejecutan) | Se ejecutan automáticamente en cada cambio |
| **Detección de errores** | Al intentar desplegar (tarde) | En minutos tras el commit (temprano) |
| **Confianza en el código** | "En mi máquina funciona" | El pipeline lo verifica en un entorno limpio |
| **Empaquetado** | Manual: `docker build` en la terminal | Automático: imagen Docker generada por el pipeline |

> **Principio fundamental:** Si duele hacerlo manualmente, automatícelo. Si lo automatiza, hágalo frecuentemente.

---

## Arquitectura CI Implementada

```
🐳 Docker Compose
├── ⚙️ Jenkins (:9090)         → Servidor CI, ejecuta pipelines
├── 🔍 SonarQube (:9000)       → Análisis de calidad de código
├── 🗄️ Sonar-DB                → PostgreSQL para SonarQube
├── 🗄️ Docker Registry (:5000) → Registry local para imágenes
├── 🐰 RabbitMQ (:5672)        → Message Broker
├── 👥 empleados-service        → Python/Flask (:8080)
├── 🔐 auth-service             → Python/Flask (:8082)
├── 📋 departamentos-service    → Python/Flask (:8086)
├── 📧 notificaciones-service   → .NET 10 (:8084)
└── 📋 perfiles-service         → Java/Spring Boot (:8083)
```

### Flujo del Pipeline

```
git push → [Trigger] → Checkout → Build → Test → SonarQube → Quality Gate → Package → Publish → E2E Tests
                                    │        │         │            │            │          │           │
                                    │        │         │            │            │          │           └── ✗ Falla → Pipeline falla
                                    │        │         │            │            │          └── docker push al registry
                                    │        │         │            │            └── docker build imagen
                                    │        │         │            └── ✗ Cobertura < 70% → Pipeline falla
                                    │        │         └── Envía análisis a SonarQube
                                    │        └── ✗ Tests fallan → Pipeline falla
                                    └── ✗ No compila → Pipeline falla
```

---

## Punto 1: Configuración de Jenkins en Docker Compose

### Decisiones Técnicas y Justificación

#### 🔌 Acceso a Docker: **Docker Socket Mount**

| Opción | Descripción | Elegida |
|--------|-------------|---------|
| **Docker Socket Mount** | Montar `/var/run/docker.sock` del host | ✅ **Sí** |
| Docker-in-Docker (DinD) | Daemon Docker dentro del contenedor | ❌ No |

**Justificación:** El Docker Socket Mount es la opción más simple y directa. Permite que Jenkins use el mismo daemon Docker del host, lo que significa que las imágenes construidas en el pipeline están inmediatamente disponibles para el sistema. En un entorno académico, el riesgo de seguridad del socket compartido es aceptable. DinD introduce complejidad innecesaria (problemas con capas de almacenamiento, rendimiento reducido).

#### 🔧 Setup Wizard: **Desactivado**

| Opción | Descripción | Elegida |
|--------|-------------|---------|
| **Desactivado** (`runSetupWizard=false`) | Plugins pre-instalados en Dockerfile | ✅ **Sí** |
| Activado | Configuración manual en primera ejecución | ❌ No |

**Justificación:** Desactivar el wizard garantiza reproducibilidad. Todos los plugins se instalan via `jenkins-plugin-cli` en el Dockerfile, por lo que al reconstruir la imagen siempre se obtiene la misma configuración sin intervención manual.

#### 📦 Plugins Pre-instalados

| Plugin | Propósito |
|--------|-----------|
| `workflow-aggregator` | Pipeline declarativo |
| `docker-pipeline` | Integración con Docker |
| `docker-workflow` | Docker como agente del pipeline |
| `pipeline-stage-view` | Visualización de etapas |
| `git` | Integración con Git |
| `configuration-as-code` | JCasC para auto-configuración |
| `job-dsl` | Definición de jobs como código |
| `sonar` | Integración con SonarQube |
| `jacoco` | Reportes de cobertura JaCoCo |
| `htmlpublisher` | Reportes HTML |
| `pipeline-utility-steps` | Utilidades del pipeline |
| `credentials-binding` | Manejo seguro de credenciales |
| `timestamper` | Timestamps en logs |
| `ws-cleanup` | Limpieza del workspace |

### Implementación

**`jenkins/Dockerfile`**: Imagen personalizada basada en `jenkins/jenkins:lts-jdk17` que:
- Pre-instala todos los plugins con `jenkins-plugin-cli`
- Instala el cliente Docker (`docker.io`) y `docker-compose`
- Agrega el usuario `jenkins` al grupo `docker`

**`docker-compose.yml`**: Servicio Jenkins con:
- Puerto `9090:8080` (interfaz web)
- Puerto `50000:50000` (comunicación con agentes)
- Volumen para Docker socket
- Variables de entorno para JCasC

---

## Punto 2: Jenkinsfiles – Build y Test

### Microservicios Elegidos

Se implementan pipelines para **2 microservicios en lenguajes diferentes**:

| Microservicio | Lenguaje | Framework | Herramienta Build | Herramienta Test |
|---|---|---|---|---|
| **empleados-service** | Python | Flask | pip | pytest + pytest-cov |
| **perfiles-service** | Java | Spring Boot | Gradle | JUnit 5 + JaCoCo |

### Decisiones Técnicas y Justificación

#### 📋 Aprovisionamiento de Jobs: **JCasC (Jenkins Configuration as Code)**

| Opción | Descripción | Elegida |
|--------|-------------|---------|
| **JCasC** | Archivo YAML que define jobs automáticamente | ✅ **Sí** |
| `init.groovy.d` | Scripts Groovy ejecutados al arrancar | ❌ No |
| Jenkinsfile local | Leer Jenkinsfile del sistema de archivos | ❌ No |

**Justificación:** JCasC es la opción más declarativa y legible. Un archivo YAML es más fácil de mantener y versionar que scripts Groovy. Además, el plugin `configuration-as-code` es el enfoque oficialmente recomendado por Jenkins para configuración reproducible. Se eligió sobre `init.groovy.d` porque:
- Es declarativo vs imperativo
- No requiere conocimiento profundo de la API de Jenkins
- Es más fácil de auditar y revisar
- Soporta configuración completa (jobs, credenciales, herramientas)

#### 🏗️ Agente del Pipeline: **Contenedores Docker efímeros**

| Opción | Descripción | Elegida |
|--------|-------------|---------|
| `agent any` | Ejecutar directamente en Jenkins | ❌ No |
| **Docker efímero** | Contenedores por etapa | ✅ **Sí** |

**Justificación:** Los contenedores Docker efímeros proporcionan aislamiento total entre ejecuciones. Cada etapa usa la imagen exacta que necesita (`python:3.11-slim` para Python, `gradle:8.14-jdk17` para Java), evitando instalar herramientas en el contenedor Jenkins. Esto garantiza:
- Reproducibilidad (misma versión de herramientas siempre)
- Aislamiento (sin conflictos entre proyectos)
- Limpieza automática (el contenedor se destruye al terminar)

#### 📦 Cache de Dependencias: **Volúmenes Docker**

**Justificación:** Se montan volúmenes (`pip-cache`, `gradle-cache`) para cachear dependencias entre ejecuciones. Esto evita que cada build descargue todas las dependencias desde cero, reduciendo significativamente el tiempo de ejecución.

### Tests Unitarios

#### empleados-service (Python)

Se creó `test_app.py` con **22 tests** organizados en clases:
- `TestHealthCheck`: Verifica endpoint `/health`
- `TestAutenticacion`: JWT, tokens inválidos/expirados, RBAC
- `TestListarEmpleados`: Paginación, roles
- `TestObtenerEmpleado`: Búsqueda por ID, 404
- `TestRegistrarEmpleado`: Validaciones, departamento, cédula duplicada
- `TestEliminarEmpleado`: Eliminación exitosa, 404
- `TestFuncionesAuxiliares`: Funciones de respuesta estándar

**Tecnologías:** pytest + pytest-cov + unittest.mock

#### perfiles-service (Java)

El proyecto ya incluye tests con JUnit 5. Se agregó:
- Plugin **JaCoCo** para cobertura de código
- Configuración para generar reportes XML (SonarQube) y HTML

**Tecnologías:** JUnit 5 + JaCoCo

---

## Punto 3: Calidad de Código con SonarQube

### Decisiones Técnicas y Justificación

#### 🔑 Token de SonarQube: **Jenkins Credentials via JCasC**

| Opción | Descripción | Elegida |
|--------|-------------|---------|
| **Jenkins Credentials** | Secret Text configurado via JCasC | ✅ **Sí** |
| Variable de entorno Docker Compose | Token en docker-compose.yml | ❌ No |
| Hardcodeado en Jenkinsfile | Token directamente en el código | ❌ No |

**Justificación:** Jenkins Credentials es la forma más segura de manejar tokens. El token se almacena encriptado en Jenkins y se inyecta como variable de entorno en tiempo de ejecución. Al configurarlo via JCasC, se provisiona automáticamente sin pasos manuales. Las otras opciones expondrían el token en archivos versionados.

#### 🚦 Quality Gate: **Personalizado (cobertura ≥ 70%)**

| Opción | Descripción | Elegida |
|--------|-------------|---------|
| "Sonar way" (default) | Cobertura ≥ 80% en código nuevo | ❌ No |
| **Personalizado** | Cobertura ≥ 70% | ✅ **Sí** |

**Justificación:** El requisito del proyecto final establece cobertura ≥ 70%. Se crea un Quality Gate personalizado alineado con este requisito. El "Sonar way" con 80% es más estricto de lo necesario para este contexto académico.

#### 🔍 Scanner: **Diferenciado por lenguaje**

| Servicio | Herramienta | Justificación |
|---|---|---|
| **empleados-service** (Python) | `sonarsource/sonar-scanner-cli` (Docker) | No requiere instalación en Jenkins. Contenedor efímero con scanner pre-instalado. |
| **perfiles-service** (Java) | Plugin Sonar Gradle (`org.sonarqube`) | Integrado nativamente en Gradle. La forma más natural y oficial para proyectos Java/Gradle. |

#### 🔗 Webhook SonarQube → Jenkins

El webhook se debe configurar en SonarQube (Administration → Webhooks) apuntando a `http://jenkins:8080/sonarqube-webhook/`. Esto permite que `waitForQualityGate` reciba el resultado del análisis.

### Configuración SonarQube

**Servicios en Docker Compose:**
- `sonarqube` (imagen `sonarqube:lts-community`, puerto 9000)
- `sonar-db` (PostgreSQL 16 Alpine para persistencia)

**Credenciales por defecto:** `admin` / `admin` (cambiar en primera ejecución)

---

## Punto 4: Empaquetado Docker y Pruebas E2E

### Decisiones Técnicas y Justificación

#### 🏷️ Naming Convention: **`proyecto-{servicio}:{BUILD_NUMBER}`**

| Opción | Ejemplo | Elegida |
|--------|---------|---------|
| Solo nombre | `empleados:latest` | ❌ No |
| **Prefijo + BUILD_NUMBER** | `proyecto-empleados:42` | ✅ **Sí** |
| Semántico + hash | `empleados:1.2.3-abc1234` | ❌ No |

**Justificación:** El prefijo `proyecto-` agrupa las imágenes del proyecto. El `BUILD_NUMBER` de Jenkins proporciona trazabilidad directa al build que generó la imagen. Se etiqueta también como `latest` para facilitar el uso en desarrollo. El versionado semántico con hash es más apropiado para producción y agrega complejidad innecesaria en este contexto.

#### 🏗️ Multi-stage Builds: **Ya implementados**

Los Dockerfiles del proyecto ya utilizan multi-stage builds:
- **empleados-service**: `python:3.11-slim AS builder` → `python:3.11-slim`
- **perfiles-service**: `gradle:8.14-jdk17 AS build` → `eclipse-temurin:17-jre-alpine`
- **notificaciones-service**: `dotnet/sdk:10.0 AS build` → `dotnet/aspnet:10.0`

El pipeline simplemente ejecuta `docker build` y el Dockerfile se encarga de la optimización.

#### 📦 Registry: **Local (registry:2)**

| Opción | Descripción | Elegida |
|--------|-------------|---------|
| **Registry local** | `registry:2` en Docker Compose, puerto 5000 | ✅ **Sí** |
| DockerHub | Registry público con autenticación | ❌ No |

**Justificación:** Un registry local es más simple, no requiere autenticación ni conexión a internet, y es ideal para un entorno de desarrollo/académico. DockerHub requeriría gestionar credenciales y tiene límites de pull rate.

#### ❤️ Health Check pre-E2E: **Script de polling**

| Opción | Descripción | Elegida |
|--------|-------------|---------|
| `sleep 30` | Espera fija | ❌ No |
| `depends_on` con condiciones | Solo para startup order | ❌ No |
| **Polling a health checks** | Script con reintentos | ✅ **Sí** |

**Justificación:** El script `wait-for-services.sh` hace polling a los endpoints de health check de cada servicio con reintentos (máximo 30 intentos, 10 segundos entre cada uno). Es más confiable que `sleep` porque espera activamente hasta que los servicios respondan. Un `sleep` podría ser insuficiente en máquinas lentas o excesivo en máquinas rápidas.

#### 🧹 Aislamiento de Datos: **`docker-compose down -v`**

**Justificación:** Se usa `docker-compose down -v` en el bloque `post { always {} }` para limpiar volúmenes después de las pruebas E2E. Esto garantiza que cada ejecución empiece con datos limpios, evitando interferencias entre ejecuciones.

### Pruebas E2E

Las pruebas E2E ejecutan la suite **BDD con Behave** del Reto 5:
1. Se levanta el sistema completo con `docker-compose up -d --build`
2. Se espera a que todos los servicios estén operativos (health check polling)
3. Se ejecuta Behave en un contenedor Python conectado a la red `checkin-net`
4. Se limpia el sistema con `docker-compose down -v`

---

## Punto 5: Reproducibilidad y Documentación

### Ejecución Consistente

Los pipelines están diseñados para ser **idempotentes**:
- Cada ejecución parte de un workspace limpio (`cleanWs()`)
- Los volúmenes E2E se limpian con `-v`
- Las dependencias se cachean pero no afectan el resultado
- Las imágenes Docker se etiquetan con `BUILD_NUMBER` único

### Simulación de Fallos

El pipeline detecta fallos en cada etapa:

| Fallo | Etapa que falla | Cómo simular |
|-------|----------------|---------------|
| Test unitario falla | **Test** | Modificar `test_app.py` con un `assert False` |
| Cobertura < 70% | **Quality Gate** | Eliminar tests para reducir cobertura |
| Dockerfile con error | **Package** | Introducir un `FROM imagen:inexistente` |
| Escenario BDD falla | **E2E Tests** | Modificar un endpoint para retornar error |

---

## Accesos

| Servicio | URL | Credenciales |
|----------|-----|-------------|
| **Jenkins** | http://localhost:9090 | `admin` / `admin123` |
| **SonarQube** | http://localhost:9000 | `admin` / `admin` (cambiar en 1er login) |
| **Docker Registry** | http://localhost:5000 | Sin autenticación |
| **RabbitMQ** | http://localhost:15672 | `admin` / `admin` |

---

## Etapas del Pipeline

| # | Etapa | Qué hace | Verde ✅ | Rojo ❌ |
|---|-------|----------|---------|--------|
| 1 | **Checkout** | Obtiene código fuente | Código descargado | Repo no accesible |
| 2 | **Build** | Compila/instala dependencias | Compilación exitosa | Error de compilación o dependencias |
| 3 | **Test** | Ejecuta tests unitarios + cobertura | Todos los tests pasan | Al menos un test falla |
| 4 | **SonarQube** | Envía código y cobertura a SonarQube | Análisis completado | SonarQube no disponible |
| 5 | **Quality Gate** | Verifica umbrales de calidad | Cobertura ≥ 70%, 0 bugs | Cobertura < 70% o bugs |
| 6 | **Package** | Construye imagen Docker | Imagen construida | Error en Dockerfile |
| 7 | **Publish** | Publica imagen al registry | Push exitoso | Registry no disponible |
| 8 | **E2E Tests** | Pruebas funcionales BDD | Todos los escenarios pasan | Al menos un escenario falla |

---

## Instrucciones de Configuración

### 1. Levantar el sistema

```bash
docker-compose up --build -d
```

### 2. Acceder a Jenkins

Abrir http://localhost:9090 en el navegador.

**Credenciales:** `admin` / `admin123`

> **Nota:** El Setup Wizard está desactivado. Jenkins se configura automáticamente con JCasC.

### 3. Configurar SonarQube

1. Acceder a http://localhost:9000
2. Login con `admin` / `admin`, cambiar contraseña
3. Crear token: **My Account → Security → Generate Token**
4. Actualizar el token en `jenkins/casc.yaml` (campo `secret` en credenciales)
5. Crear Quality Gate personalizado:
   - **Administration → Quality Gates → Create**
   - Agregar condición: **Coverage ≥ 70%**
   - Establecer como default
6. Configurar webhook:
   - **Administration → Configuration → Webhooks → Create**
   - URL: `http://jenkins:8080/sonarqube-webhook/`

### 4. Ejecutar un pipeline

1. En Jenkins, ir al job (ej. `empleados-service-pipeline`)
2. Click en **"Build Now"**
3. Observar las etapas en **"Stage View"**
4. Click en cada etapa para ver los logs detallados

---

## Estructura de Archivos (Reto 6)

```
ProyectoFinalMicroservicios/
├── jenkins/
│   ├── Dockerfile              # Imagen personalizada de Jenkins
│   ├── casc.yaml               # Configuración JCasC (jobs + credenciales)
│   └── wait-for-services.sh    # Script health check para E2E
├── empleados-service/
│   ├── Jenkinsfile             # Pipeline CI (Python)
│   ├── test_app.py             # Tests unitarios (pytest)
│   ├── sonar-project.properties # Config SonarQube Scanner
│   └── ...
├── perfiles-service/
│   ├── Jenkinsfile             # Pipeline CI (Java/Gradle)
│   ├── build.gradle            # Actualizado con JaCoCo + Sonar
│   └── ...
├── docker-compose.yml          # Actualizado con Jenkins, SonarQube, Registry
└── RETO6_CI.md                 # Este documento
```

---

## Resumen de Decisiones

| Decisión | Opción Elegida | Alternativa Descartada |
|----------|---------------|----------------------|
| Docker access | Docker Socket Mount | Docker-in-Docker |
| Setup Wizard | Desactivado | Configuración manual |
| Aprovisionamiento jobs | JCasC | init.groovy.d / Jenkinsfile local |
| Agente pipeline | Docker efímero | agent any |
| Cache dependencias | Volúmenes Docker | Sin cache |
| Token SonarQube | Jenkins Credentials (JCasC) | Variable de entorno / Hardcoded |
| Quality Gate | Personalizado (≥70%) | Sonar way (≥80%) |
| Scanner Python | sonar-scanner-cli (Docker) | Instalación en Jenkins |
| Scanner Java | Plugin Sonar Gradle | sonar-scanner genérico |
| Naming convention | `proyecto-{servicio}:{BUILD}` | Semántico / Solo nombre |
| Registry | Local (registry:2) | DockerHub |
| Health check E2E | Script de polling | sleep / depends_on |
| Aislamiento datos | `docker-compose down -v` | Sin limpieza |
