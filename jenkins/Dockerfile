# ============================================================
# Jenkins - Dockerfile Personalizado para CI Pipeline
# Reto 6 - Integración Continua
# ============================================================
FROM jenkins/jenkins:lts-jdk17

# ============================================================
# Pre-instalar plugins necesarios con jenkins-plugin-cli
# Referencia: https://github.com/jenkinsci/docker#preinstalling-plugins
# ============================================================
RUN jenkins-plugin-cli --plugins \
    workflow-aggregator \
    docker-workflow \
    docker-commons \
    pipeline-stage-view \
    git \
    configuration-as-code \
    job-dsl \
    sonar \
    jacoco \
    htmlpublisher \
    pipeline-utility-steps \
    credentials-binding \
    timestamper \
    ws-cleanup

# ============================================================
# Instalar cliente Docker dentro del contenedor Jenkins
# Estrategia: Docker Socket Mount (montar el socket del host)
# ============================================================
USER root

RUN apt-get update && \
    apt-get install -y \
        docker.io \
        docker-compose \
        curl \
        jq \
    && rm -rf /var/lib/apt/lists/*

# Agregar usuario jenkins al grupo docker para acceder al socket
RUN groupadd -f docker && usermod -aG docker jenkins

# ============================================================
# Volver al usuario jenkins
# ============================================================
USER jenkins
