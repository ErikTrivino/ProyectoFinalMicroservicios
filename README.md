# ProyectoFinalMicroservicios

Sistema de gestión de empleados basado en arquitectura de microservicios con comunicación asincrónica.

## Integrantes
- Erik Pablo Triviño Gonzalez
- Felip Valencia Londoño
- Anderson Betancurt
- Jose Felipe Gabinos

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Docker Network (checkin-net)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ empleados-service│     │departamentos-svc │     │ perfiles-service │    │
│  │     :8080        │────▶│     :8081        │     │     :8083        │    │
│  │    (Python)      │REST │    (Python)      │     │  (Spring Boot)   │    │
│  └────────┬─────────┘     └──────────────────┘     └────────▲─────────┘    │
│           │                                                 │              │
│           │ Publica eventos                    Consume eventos             │
│           ▼                                                 │              │
│  ┌────────────────────────────────────────────────────────┐│              │
│  │              RabbitMQ (message-broker)                  ││              │
│  │  Exchanges: empleado.creado, empleado.eliminado        │├──────────┐   │
│  │                    :5672 / :15672                       ││          │   │
│  └────────────────────────────────────────────────────────┘│          │   │
│                                                 │          │          │   │
│                                    Consume eventos         │          │   │
│                                                 ▼          │          │   │
│                                    ┌──────────────────┐    │          │   │
│                                    │notificaciones-svc│◀───┘          │   │
│                                    │     :8084        │               │   │
│                                    │     (.NET)       │               │   │
│                                    └──────────────────┘               │   │
│                                                                       │   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │db-empleados │ │db-departam. │ │ db-perfiles │ │db-notificac.│     │   │
│  │   :5437     │ │   :5438     │ │   :5439     │ │   :5440     │     │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘     │   │
│                                                                       │   │
└───────────────────────────────────────────────────────────────────────┘   │

```

---

## Elección del Message Broker

### Investigación de alternativas

| Broker | Características | Pros | Contras |
|--------|-----------------|------|---------|
| **RabbitMQ** | Protocolo AMQP, exchanges/colas, UI de gestión | Fácil configuración, buena documentación, UI administrativa | Menor throughput que Kafka |
| **Apache Kafka** | Alto throughput, persistencia, streaming | Excelente para grandes volúmenes | Más complejo de configurar |
| **Redis Streams** | Ligero, bajo overhead | Mínimo consumo de recursos | Menos features de mensajería |
| **NATS** | Ultra-ligero, cloud-native | Alta performance | Menos maduro en ecosistema |

### Justificación de RabbitMQ

Elegimos **RabbitMQ** por las siguientes razones:

1. **Patrón Fan-out nativo**: Los exchanges tipo `fanout` permiten que un evento sea consumido por múltiples servicios de forma sencilla (perfiles y notificaciones reciben el mismo evento).

2. **Interfaz de administración**: La UI en puerto `15672` facilita el debugging y monitoreo de colas/mensajes.

3. **Amplia documentación**: Existen librerías maduras para Python (`pika`), Java (`spring-amqp`) y .NET (`RabbitMQ.Client`).

4. **Simplicidad**: Para el volumen de mensajes de este sistema, RabbitMQ ofrece un balance ideal entre funcionalidad y complejidad.

5. **Persistencia configurable**: Los mensajes se pueden marcar como `durable` para sobrevivir reinicios del broker.

---

## Documentación de Eventos

### Evento: `empleado.creado`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| Exchange | `empleado.creado` | Exchange tipo fanout |
| Productor | `empleados-service` | Se publica al crear un empleado exitosamente |
| Consumidores | `perfiles-service`, `notificaciones-service` | Ambos servicios escuchan este evento |

**Payload:**
```json
{
  "id": "uuid-del-empleado",
  "nombre": "Juan Pérez",
  "email": "juan@empresa.com",
  "departamentoId": "IT",
  "fechaIngreso": "2024-01-15"
}
```

**Acciones desencadenadas:**
- `perfiles-service`: Crea un perfil por defecto para el empleado
- `notificaciones-service`: Registra y simula envío de email de bienvenida

---

### Evento: `empleado.eliminado`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| Exchange | `empleado.eliminado` | Exchange tipo fanout |
| Productor | `empleados-service` | Se publica al eliminar un empleado |
| Consumidores | `notificaciones-service` | Escucha para notificar desvinculación |

**Payload:**
```json
{
  "id": "uuid-del-empleado",
  "nombre": "Juan Pérez",
  "email": "juan@empresa.com"
}
```

**Acciones desencadenadas:**
- `notificaciones-service`: Registra y simula notificación de desvinculación

---

## Servicios

| Servicio | Puerto | Tecnología | Descripción |
|----------|--------|------------|-------------|
| empleados-service | 8080 | Python/Flask | CRUD de empleados, publica eventos |
| departamentos-service | 8081 | Python/Flask | CRUD de departamentos |
| perfiles-service | 8083 | Java/Spring Boot | Gestión de perfiles, consume eventos |
| notificaciones-service | 8084 | C#/.NET | Registro de notificaciones, consume eventos |
| message-broker | 5672/15672 | RabbitMQ | Broker de mensajes |

---

## Instrucciones de Despliegue

### Prerequisitos
- Docker Desktop instalado
- Docker Compose v2+
- Puertos disponibles: 8080-8084, 5672, 15672, 5437-5440

### Despliegue completo

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd ProyectoFinalMicroservicios

# Iniciar todos los servicios
docker-compose up --build

# O en segundo plano
docker-compose up --build -d
```

### Verificar servicios

```bash
# Ver estado de contenedores
docker-compose ps

# Ver logs de un servicio específico
docker-compose logs -f notificaciones-service
```

### Detener servicios

```bash
docker-compose down

# Para eliminar también los volúmenes (datos)
docker-compose down -v
```

---

## Endpoints Disponibles

### Swagger UI
- Empleados: http://localhost:8080/apidocs
- Departamentos: http://localhost:8081/apidocs
- Perfiles: http://localhost:8083/swagger-ui.html
- Notificaciones: http://localhost:8084/swagger

### RabbitMQ Management
- URL: http://localhost:15672
- Usuario: `admin`
- Password: `admin`

---

## Instrucciones de Prueba

### 1. Iniciar servicios
```bash
docker-compose up --build
```

### 2. Verificar RabbitMQ
Acceder a http://localhost:15672 (admin/admin) y verificar que los exchanges `empleado.creado` y `empleado.eliminado` existen.

### 3. Crear un departamento
```bash
curl -X POST http://localhost:8081/departamentos \
  -H "Content-Type: application/json" \
  -d '{"id": "IT", "nombre": "Tecnología", "descripcion": "Departamento de TI"}'
```

### 4. Crear un empleado (dispara eventos)
```bash
curl -X POST http://localhost:8080/empleados \
  -H "Content-Type: application/json" \
  -d '{
    "cedula": "123456789",
    "nombre": "Juan Pérez",
    "email": "juan@empresa.com",
    "departamentoId": "IT",
    "fechaIngreso": "2024-01-15"
  }'
```

**Guardar el `id` retornado para los siguientes pasos.**

### 5. Verificar perfil creado automáticamente
```bash
curl http://localhost:8083/perfiles/{empleadoId}
```

### 6. Verificar notificación de bienvenida
```bash
curl http://localhost:8084/notificaciones/{empleadoId}
```

### 7. Actualizar perfil del empleado
```bash
curl -X PUT http://localhost:8083/perfiles/{empleadoId} \
  -H "Content-Type: application/json" \
  -d '{
    "telefono": "3001234567",
    "ciudad": "Armenia",
    "biografia": "Ingeniero de sistemas"
  }'
```

### 8. Eliminar empleado (dispara evento de desvinculación)
```bash
curl -X DELETE http://localhost:8080/empleados/{empleadoId}
```

### 9. Verificar notificación de desvinculación
```bash
curl http://localhost:8084/notificaciones/{empleadoId}
```

### 10. Verificar persistencia
```bash
# Reiniciar contenedores
docker-compose restart

# Verificar que los datos persisten
curl http://localhost:8084/notificaciones
```

---

## Logs de Notificaciones Simuladas

El servicio de notificaciones imprime logs estructurados simulando el envío:

```
[NOTIFICACIÓN] Tipo: BIENVENIDA | Para: juan@empresa.com | Mensaje: "Bienvenido Juan Pérez..."
[NOTIFICACIÓN] Tipo: DESVINCULACION | Para: juan@empresa.com | Mensaje: "Su cuenta ha sido desactivada..."
```

Ver logs en tiempo real:
```bash
docker-compose logs -f notificaciones-service
```