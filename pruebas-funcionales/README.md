# Suite de Pruebas E2E - Onboarding & Offboarding

Esta carpeta contiene la suite de pruebas funcionales automatizadas para el sistema de microservicios de gestión de empleados. Las pruebas están diseñadas siguiendo la metodología **BDD (Behavior-Driven Development)** para validar los flujos de negocio desde la perspectiva del usuario.

## 🚀 Cómo Ejecutar

### Prerrequisitos
1.  **Microservicios arriba**: Asegúrese de que el sistema base esté corriendo con `docker-compose up -d`.
2.  **Python 3.10+**: Las pruebas requieren Python instalado.
3.  **Dependencias**: Instale los requerimientos necesarios:
    ```bash
    pip install -r e2e-tests/requirements.txt
    ```

### Comando Único de Ejecución
Como requiere el reto, se dispone de un script que ejecuta la suite completa **3 veces seguidas** para validar la consistencia y ausencia de fallos intermitentes (flaky tests):

```bash
python e2e-tests/run_all.py
```

---

## 🧠 Metodología BDD
**Behavior-Driven Development** es una técnica de desarrollo ágil que fomenta la colaboración entre desarrolladores, QA y perfiles no técnicos. 

- **Lenguaje Natural (Gherkin)**: Los escenarios están escritos en español utilizando palabras clave como `Dado`, `Cuando` y `Entonces`.
- **Enfoque en el usuario**: No probamos métodos de código, probamos comportamientos del sistema (ej: "Un administrador registra un empleado").
- **Documentación Viva**: Los archivos `.feature` sirven tanto de especificación como de prueba ejecutable.

---

## 🛠️ Herramientas Utilizadas
-   **Behave**: El framework de BDD para Python (implementación de Cucumber).
-   **Requests**: Librería para realizar peticiones HTTP a las APIs de los microservicios.
-   **Python-dotenv**: Para la gestión de variables de entorno (URL de servicios, credenciales).

---

## 📋 Flujos Cubiertos

### 1. Seguridad (RBAC)
-   Validación de acceso denegado sin token (401).
-   Validación de acceso con token inválido.
-   Diferenciación de permisos entre el rol `USER` (solo lectura) y `ADMIN` (total).

### 2. Onboarding (Asíncrono)
-   Registro de empleado por un ADMIN.
-   **Polling de Notificaciones**: El sistema espera asíncronamente a que el `notificaciones-service` procese el evento para capturar el token de seguridad generado.
-   Activación de cuenta y verificación de Login exitoso.

### 3. Offboarding
-   Creación de precondiciones (empleado activo).
-   Eliminación del empleado por el administrador.
-   Verificación de revocación de acceso: el empleado desvinculado ya no puede iniciar sesión.

---

## ⚙️ Configuración (.env)
Las pruebas utilizan el archivo `e2e-tests/.env` para localizar los servicios. Si sus puertos de Docker son diferentes, ajústelos allí:
- `AUTH_URL`: Puerto 8082
- `EMPLEADOS_URL`: Puerto 8080
- `NOTIFICACIONES_URL`: Puerto 8084
