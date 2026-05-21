# API Gateway

Punto unico de entrada para los clientes.

Puerto local:

```text
http://localhost:8088
```

Documentacion OpenAPI:

```text
http://localhost:8088/apidocs
http://localhost:8088/apispec_1.json
```

Rutas expuestas:

```text
POST /auth/login
POST /auth/change-password



GET /empleados?page=1&size=10
POST /empleados
GET /empleados/{id}
PUT /empleados/{id}
DELETE /empleados/{id}

GET /departamentos?page=1&size=10
POST /departamentos
GET /departamentos/{id}

GET /perfiles
GET /perfiles/{empleadoId}
PUT /perfiles/{empleadoId}

POST /vacaciones
GET /vacaciones/{cedula}
PUT /vacaciones/{id}/estado

GET /notificaciones
GET /notificaciones/{empleadoId}
```



Notas:

- El gateway valida JWT antes de llamar endpoints protegidos.
- `GET /empleados/{id}` compone la respuesta con datos de `empleados-service` y `perfiles-service`.
- `GET /perfiles` y `PUT /perfiles` operan sobre el perfil del empleado autenticado.
- `GET /vacaciones` acepta `?cedula=...`; si no se envia, intenta resolver la cedula usando el `empleadoId` del token.
- No existe registro publico. Los usuarios se crean por eventos cuando RRHH registra empleados.
