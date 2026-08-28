# DiabCare — detener stack (pareja de .\arrancar.ps1)
# Uso:  .\detener.ps1                detener todo
#       .\detener.ps1 -SoloBackend   reinicio rapido durante desarrollo

param(
    [switch]$SoloBackend
)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$Contenedores = @(
    "minio", "pocketbase",
    "diabcare-airflow-webserver-1", "diabcare-airflow-scheduler-1",
    "diabcare-airflow-worker-1", "diabcare-airflow-triggerer-1",
    "diabcare-airflow-init-1",
    "diabcare-postgres-1", "diabcare-redis-1"
)

Write-Host "[1/3] Backend (:8000)..." -ForegroundColor Cyan
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "      Backend detenido." -ForegroundColor Green
} else {
    Write-Host "      No habia backend en :8000." -ForegroundColor Yellow
}

if ($SoloBackend) {
    Write-Host ""
    Write-Host "Listo. Los contenedores siguen activos." -ForegroundColor White
    exit 0
}

Write-Host "[2/3] Airflow (compose)..." -ForegroundColor Cyan
if (Test-Path ".\docker-compose.airflow.yml") {
    docker compose -f docker-compose.airflow.yml stop -t 2 *> $null
    Write-Host "      Compose Airflow stop enviado." -ForegroundColor Green
}

Write-Host "[3/3] Contenedores MinIO / PocketBase / resto..." -ForegroundColor Cyan
docker info *> $null
if ($LASTEXITCODE -eq 0) {
    docker stop -t 2 $Contenedores *> $null
    Write-Host "      Contenedores detenidos." -ForegroundColor Green
} else {
    Write-Host "      Docker no disponible." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Listo. Docker Desktop puede quedar abierto." -ForegroundColor White
