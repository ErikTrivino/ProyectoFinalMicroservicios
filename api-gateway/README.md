# API Gateway

Punto unico de entrada para los clientes.

Puerto local:

```text
http://localhost:8088
```

Rutas expuestas:

```text
POST /auth/login
POST /auth/change-password
GET /employees
POST /employees
GET /employees/{id}
PUT /employees/{id}
DELETE /employees/{id}
GET /profile
PUT /profile
POST /vacations
GET /vacations
```

Notas:

- El gateway valida JWT antes de llamar endpoints protegidos.
- `GET /employees/{id}` compone la respuesta con datos de `empleados-service` y `perfiles-service`.
- `GET /vacations` acepta `?cedula=...`; si no se envia, intenta resolver la cedula usando el `empleadoId` del token.
- No existe registro publico. Los usuarios se crean por eventos cuando RRHH registra empleados.
