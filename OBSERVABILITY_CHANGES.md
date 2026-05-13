# Cambios aplicados en Observabilidad

## Archivos nuevos / modificados

1. `observability/grafana/provisioning/datasources/datasource.yml`
   - Define los orígenes de datos de Grafana:
     - Prometheus (`http://prometheus:9090`)
     - Loki (`http://loki:3100`)
     - Zipkin (`http://zipkin:9411`)

2. `observability/grafana/provisioning/dashboards/dashboard.yml`
   - Configura la provisión de dashboard de Grafana para importar el JSON desde el disco.

3. `observability/grafana/provisioning/dashboards/dashboard.json`
   - Dashboard versionado con 4 paneles:
     - Estado
     - Tasa de peticiones
     - Latencia promedio
     - Errores 4xx/5xx
   - Incluye alertas:
     - Servicio caído
     - Alta tasa de errores 5xx
   - Usa métricas adaptadas a los tres lenguajes del stack (Python, Java, C#).

4. `observability/grafana/provisioning/notifiers/discord-webhook.yml`
   - Define un canal de notificación de Grafana vía Discord webhook.

5. `docker-compose.yml`
   - Actualiza el servicio `grafana` para montar:
     - `/etc/grafana/provisioning` desde `./observability/grafana/provisioning`
     - `/var/lib/grafana/dashboards` desde `./observability/grafana/provisioning/dashboards`

6. `README.md`
   - Agrega la sección de observabilidad con:
     - ruta del dashboard JSON versionado
     - consultas PromQL adaptadas al stack mixto
     - consulta LogQL de ejemplo para Loki
     - instrucciones breves para validar Grafana y Loki

## Pruebas realizadas

- Validé el JSON de `observability/grafana/provisioning/dashboards/dashboard.json` con Python.
- Validé la sintaxis de `docker-compose.yml` usando `docker-compose config`.

## Resultado

El archivo de dashboard está listo para ser importado por Grafana al iniciar el contenedor, y la configuración de Grafana está preparada para cargar los orígenes y los paneles de observabilidad.

> Si quieres, puedo continuar ahora con la documentación de conceptos (`Pull/Push`, `OTel`, `W3C Trace Context`, `Zipkin vs Jaeger`) o con pruebas reales de la stack levantada en Docker para verificar los paneles y las alertas en acción.
