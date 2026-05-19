# ============================
# Etapa 1: Build con Gradle
# ============================
FROM gradle:8.14-jdk17 AS build
WORKDIR /app

# Copiar archivos de configuración de Gradle primero (cachea dependencias)
COPY build.gradle settings.gradle ./
COPY gradle ./gradle

# Descargar dependencias (se cachea si no cambian)
RUN gradle dependencies --no-daemon

# Copiar código fuente y compilar
COPY src ./src
RUN gradle clean build -x test --no-daemon

# ============================
# Etapa 2: Runtime ligero
# ============================
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

# Copiar el JAR construido
COPY --from=build /app/build/libs/*.jar app.jar

# Puerto del servicio
EXPOSE 8083

# Comando de inicio
ENTRYPOINT ["java", "-jar", "app.jar"]