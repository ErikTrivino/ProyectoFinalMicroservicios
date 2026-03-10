# =========================
# Etapa 1: build
# =========================
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build

WORKDIR /src

# Copiar csproj y restaurar
COPY NotificacionesService.csproj .
RUN dotnet restore

# Copiar todo el codigo y compilar
COPY . .
RUN dotnet publish -c Release -o /app/publish

# =========================
# Etapa 2: runtime
# =========================
FROM mcr.microsoft.com/dotnet/aspnet:10.0

WORKDIR /app

# Copiar desde build
COPY --from=build /app/publish .

# Puerto del servicio
EXPOSE 8084

# Variables de entorno (se sobreescriben en docker-compose)
ENV ASPNETCORE_URLS=http://+:8084
ENV ASPNETCORE_ENVIRONMENT=Production

ENTRYPOINT ["dotnet", "NotificacionesService.dll"]
