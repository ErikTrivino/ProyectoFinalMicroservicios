# Script de Pruebas Rápidas - Microservicios JWT (PowerShell)
# Uso: powershell -ExecutionPolicy Bypass -File test-api.ps1

param(
    [switch]$SkipSummary = $false
)

# URLs base
$authUrl = "http://localhost:8082"
$empleadosUrl = "http://localhost:8080"

# Variables globales
$adminToken = ""
$userToken = ""

# Función para mostrar títulos
function Show-Title {
    param([string]$title)
    Write-Host "`n========================================" -ForegroundColor Blue
    Write-Host "  $title" -ForegroundColor Blue
    Write-Host "========================================`n" -ForegroundColor Blue
}

# Función auxiliar para requests
function Invoke-ApiRequest {
    param(
        [string]$Method,
        [string]$Endpoint,
        [string]$Url,
        [object]$Body,
        [string]$Token
    )
    
    $headers = @{
        "Content-Type" = "application/json"
    }
    
    if ($Token) {
        $headers["Authorization"] = "Bearer $Token"
    }
    
    $bodyJson = $Body | ConvertTo-Json
    
    try {
        $response = Invoke-WebRequest -Uri "$url$endpoint" `
            -Method $Method `
            -Headers $headers `
            -Body $bodyJson `
            -ErrorAction Stop
        return $response
    }
    catch {
        return $_.Exception.Response
    }
}

# ==================== INICIO ====================
Show-Title "Pruebas de Microservicios JWT"

# ==================== PRUEBA 1: Health Check ====================
Write-Host "1. Health Check" -ForegroundColor Blue
Write-Host "---" -ForegroundColor Gray

try {
    $health = Invoke-WebRequest -Uri "$authUrl/health" -Method GET -Headers @{"Content-Type" = "application/json"}
    $health.Content | ConvertFrom-Json | ConvertTo-Json | Write-Host
    Write-Host "`n✓ PASSED`n" -ForegroundColor Green
}
catch {
    Write-Host "`n✗ FAILED: $_`n" -ForegroundColor Red
}

# ==================== PRUEBA 2: Registrar Usuario ====================
Write-Host "2. Registrar Usuario" -ForegroundColor Blue
Write-Host "---" -ForegroundColor Gray

$registerData = @{
    username = "test_user"
    email    = "test@ejemplo.com"
    password = "TestPass123"
}

try {
    $registerResponse = Invoke-WebRequest -Uri "$authUrl/auth/register" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json"} `
        -Body ($registerData | ConvertTo-Json)
    
    $registerResponse.Content | ConvertFrom-Json | ConvertTo-Json | Write-Host
    Write-Host "`n✓ PASSED`n" -ForegroundColor Green
}
catch {
    Write-Host "`n✗ FAILED: $_`n" -ForegroundColor Red
}

# ==================== PRUEBA 3: Login ADMIN ====================
Write-Host "3. Login como ADMIN (Por Defecto)" -ForegroundColor Blue
Write-Host "---" -ForegroundColor Gray

$loginAdminData = @{
    username = "admin"
    password = "admin123"
}

try {
    $loginAdminResponse = Invoke-WebRequest -Uri "$authUrl/auth/login" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json"} `
        -Body ($loginAdminData | ConvertTo-Json)
    
    $adminResponse = $loginAdminResponse.Content | ConvertFrom-Json
    $adminResponse | ConvertTo-Json | Write-Host
    
    $adminToken = $adminResponse.data.access_token
    
    Write-Host "`n✓ PASSED - Token obtenido`n" -ForegroundColor Green
    Write-Host "Token ADMIN: $($adminToken.Substring(0, 50))...`n" -ForegroundColor Yellow
}
catch {
    Write-Host "`n✗ FAILED: $_`n" -ForegroundColor Red
}

# ==================== PRUEBA 4: Login Usuario Registrado ====================
Write-Host "4. Login como USER (Registrado)" -ForegroundColor Blue
Write-Host "---" -ForegroundColor Gray

$loginUserData = @{
    username = "test_user"
    password = "TestPass123"
}

try {
    $loginUserResponse = Invoke-WebRequest -Uri "$authUrl/auth/login" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json"} `
        -Body ($loginUserData | ConvertTo-Json)
    
    $userResponse = $loginUserResponse.Content | ConvertFrom-Json
    $userResponse | ConvertTo-Json | Write-Host
    
    $userToken = $userResponse.data.access_token
    
    Write-Host "`n✓ PASSED - Token obtenido`n" -ForegroundColor Green
    Write-Host "Token USER: $($userToken.Substring(0, 50))...`n" -ForegroundColor Yellow
}
catch {
    Write-Host "`n✗ FAILED: $_`n" -ForegroundColor Red
}

# ==================== PRUEBA 5: GET Empleados (CON TOKEN ADMIN) ====================
Write-Host "5. GET /empleados (CON TOKEN ADMIN)" -ForegroundColor Blue
Write-Host "---" -ForegroundColor Gray

try {
    $getEmpleados = Invoke-WebRequest -Uri "$empleadosUrl/empleados" `
        -Method GET `
        -Headers @{
            "Content-Type"  = "application/json"
            "Authorization" = "Bearer $adminToken"
        }
    
    $getEmpleados.Content | ConvertFrom-Json | ConvertTo-Json | Write-Host
    Write-Host "`n✓ PASSED (200 OK)`n" -ForegroundColor Green
}
catch {
    Write-Host "`n✗ FAILED: $_`n" -ForegroundColor Red
}

# ==================== PRUEBA 6: GET Empleados (CON TOKEN USER) ====================
Write-Host "6. GET /empleados (CON TOKEN USER) - Debe funcionar (solo lectura)" -ForegroundColor Blue
Write-Host "---" -ForegroundColor Gray

try {
    $getEmpleadosUser = Invoke-WebRequest -Uri "$empleadosUrl/empleados" `
        -Method GET `
        -Headers @{
            "Content-Type"  = "application/json"
            "Authorization" = "Bearer $userToken"
        }
    
    $getEmpleadosUser.Content | ConvertFrom-Json | ConvertTo-Json | Write-Host
    Write-Host "`n✓ PASSED (200 OK) - USER puede leer`n" -ForegroundColor Green
}
catch {
    Write-Host "`n✗ FAILED: $_`n" -ForegroundColor Red
}

# ==================== PRUEBA 7: GET Empleados (SIN TOKEN) ====================
Write-Host "7. GET /empleados (SIN TOKEN) - Debe devolver 401" -ForegroundColor Blue
Write-Host "---" -ForegroundColor Gray

try {
    $getEmpleadosNoToken = Invoke-WebRequest -Uri "$empleadosUrl/empleados" `
        -Method GET `
        -Headers @{"Content-Type" = "application/json"} `
        -ErrorAction Stop
    
    Write-Host "`n✗ FAILED - Debería haber retornado 401`n" -ForegroundColor Red
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    Write-Host "HTTP Status: $statusCode" -ForegroundColor Yellow
    
    if ($statusCode -eq 401) {
        Write-Host "`n✓ PASSED - Correctamente rechazado (401 Unauthorized)`n" -ForegroundColor Green
    }
    else {
        Write-Host "`n✗ FAILED - Esperaba 401, recibió $statusCode`n" -ForegroundColor Red
    }
}

# ==================== PRUEBA 8: POST Empleados (ADMIN) ====================
Write-Host "8. POST /empleados (ADMIN) - Debe funcionar" -ForegroundColor Blue
Write-Host "---" -ForegroundColor Gray

$postEmpleado = @{
    nombre           = "Carlos López"
    departamento_id  = "D001"
}

try {
    $postResponse = Invoke-WebRequest -Uri "$empleadosUrl/empleados" `
        -Method POST `
        -Headers @{
            "Content-Type"  = "application/json"
            "Authorization" = "Bearer $adminToken"
        } `
        -Body ($postEmpleado | ConvertTo-Json)
    
    $postResponse.Content | ConvertFrom-Json | ConvertTo-Json | Write-Host
    Write-Host "`n✓ PASSED (201/200 Created)`n" -ForegroundColor Green
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    Write-Host "Status: $statusCode`n" -ForegroundColor Yellow
    $_.Exception.Response.Content | Write-Host
}

# ==================== PRUEBA 9: POST Empleados (USER) ====================
Write-Host "`n9. POST /empleados (USER) - Debe devolver 403 Forbidden" -ForegroundColor Blue
Write-Host "---" -ForegroundColor Gray

try {
    $postUserResponse = Invoke-WebRequest -Uri "$empleadosUrl/empleados" `
        -Method POST `
        -Headers @{
            "Content-Type"  = "application/json"
            "Authorization" = "Bearer $userToken"
        } `
        -Body ($postEmpleado | ConvertTo-Json) `
        -ErrorAction Stop
    
    Write-Host "`n✗ FAILED - Debería haber retornado 403`n" -ForegroundColor Red
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    Write-Host "HTTP Status: $statusCode" -ForegroundColor Yellow
    
    if ($statusCode -eq 403) {
        Write-Host "`n✓ PASSED - Correctamente denegado (403 Forbidden)`n" -ForegroundColor Green
    }
    else {
        Write-Host "`n✗ FAILED - Esperaba 403, recibió $statusCode`n" -ForegroundColor Red
    }
}

# ==================== PRUEBA 10: Validar Token ====================
Write-Host "10. Validar Token JWT" -ForegroundColor Blue
Write-Host "---" -ForegroundColor Gray

$validateData = @{
    token = $adminToken
}

try {
    $validateResponse = Invoke-WebRequest -Uri "$authUrl/auth/validate" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json"} `
        -Body ($validateData | ConvertTo-Json)
    
    $validateResponse.Content | ConvertFrom-Json | ConvertTo-Json | Write-Host
    Write-Host "`n✓ PASSED - Token válido`n" -ForegroundColor Green
}
catch {
    Write-Host "`n✗ FAILED: $_`n" -ForegroundColor Red
}

# ==================== RESUMEN ====================
if (-not $SkipSummary) {
    Show-Title "Pruebas Completadas"
    
    Write-Host "Tokens para referencia:" -ForegroundColor Yellow
    Write-Host "ADMIN_TOKEN: $($adminToken.Substring(0, 50))...`n" -ForegroundColor Cyan
    Write-Host "USER_TOKEN:  $($userToken.Substring(0, 50))...`n" -ForegroundColor Cyan
    
    Write-Host "Próximos pasos:" -ForegroundColor Yellow
    Write-Host "1. Revisar los logs de los servicios"
    Write-Host "   docker-compose logs -f auth-service`n"
    
    Write-Host "2. Probar en Swagger UI:"
    Write-Host "   http://localhost:8082/apidocs/`n"
    
    Write-Host "3. Monitorear RabbitMQ:"
    Write-Host "   http://localhost:15672 (admin:admin)`n"
    
    Write-Host "========================================`n" -ForegroundColor Blue
}
