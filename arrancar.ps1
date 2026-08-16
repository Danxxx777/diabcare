# DiabCare - un solo arranque (todo el stack de exhibicion)
#
# Uso:
#   .\arrancar.ps1
#   Ctrl+Shift+B  -> tarea "DiabCare: arrancar todo"
#
# Levanta: Docker Desktop -> MinIO -> PocketBase -> Airflow (DAGs ELT) -> FastAPI

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$DockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$ContenedoresBase = @("minio", "pocketbase")

function Test-DockerListo {
    docker info *> $null
    return ($LASTEXITCODE -eq 0)
}

function Test-Puerto([int]$Puerto) {
    try {
        $c = New-Object Net.Sockets.TcpClient
        $ok = $c.ConnectAsync("127.0.0.1", $Puerto).Wait(1500)
        $c.Close()
        return $ok
    } catch { return $false }
}

function Wait-Puerto([int]$Puerto, [string]$Nombre, [int]$MaxSeg = 90) {
    $espera = 0
    while (-not (Test-Puerto $Puerto)) {
        Start-Sleep -Seconds 2
        $espera += 2
        if ($espera -ge $MaxSeg) {
            Write-Host "      AVISO: $Nombre (:$Puerto) no respondio en ${MaxSeg}s." -ForegroundColor Yellow
            return $false
        }
    }
    Write-Host "      $Nombre listo (:$Puerto)." -ForegroundColor Green
    return $true
}

function Import-DotEnv([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
        $i = $line.IndexOf("=")
        $k = $line.Substring(0, $i).Trim()
        $v = $line.Substring($i + 1).Trim().Trim('"').Trim("'")
        if ($k -and -not [Environment]::GetEnvironmentVariable($k, "Process")) {
            Set-Item -Path "Env:$k" -Value $v
        }
    }
}

# --- 0. Variables de entorno locales (.env) ---
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Import-DotEnv $envFile
    Write-Host "[0/5] .env cargado." -ForegroundColor DarkGray
} else {
    Write-Host "[0/5] Sin .env - generando uno local..." -ForegroundColor Yellow
    py -3 "$PSScriptRoot\scripts\generar_env_local.py"
    Import-DotEnv $envFile
    Write-Host "      .env creado. Si PocketBase falla, edita POCKETBASE_EMAIL/PASSWORD." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========== DiabCare - arranque completo ==========" -ForegroundColor Cyan
Write-Host ""

# --- 1. Docker Desktop ---
Write-Host "[1/5] Docker Desktop..." -ForegroundColor Cyan
if (-not (Test-DockerListo)) {
    if (-not (Test-Path $DockerDesktop)) {
        Write-Host "      ERROR: No se encontro Docker Desktop en:" -ForegroundColor Red
        Write-Host "      $DockerDesktop" -ForegroundColor Red
        exit 1
    }
    Write-Host "      Arrancando Docker Desktop (puede tardar 1-2 min)..." -ForegroundColor Yellow
    Start-Process $DockerDesktop
    $espera = 0
    while (-not (Test-DockerListo)) {
        Start-Sleep -Seconds 5
        $espera += 5
        if ($espera -ge 240) {
            Write-Host "      ERROR: Docker no respondio en 4 minutos." -ForegroundColor Red
            exit 1
        }
    }
}
Write-Host "      Docker listo." -ForegroundColor Green

# --- 2. MinIO + PocketBase ---
Write-Host "[2/5] MinIO + PocketBase..." -ForegroundColor Cyan
docker start $ContenedoresBase *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "      AVISO: docker start minio/pocketbase fallo. Existen los contenedores?" -ForegroundColor Yellow
    Write-Host "      Crealos una vez o revisa Docker Desktop." -ForegroundColor Yellow
}
$null = Wait-Puerto 9000 "MinIO" 60
$null = Wait-Puerto 8090 "PocketBase" 60

# --- 3. Airflow (DAGs ELT E-L-T) ---
Write-Host "[3/5] Apache Airflow (orquestador ELT)..." -ForegroundColor Cyan
if (Test-Path ".\docker-compose.airflow.yml") {
    docker compose -f docker-compose.airflow.yml up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      AVISO: compose Airflow devolvio error; se intenta seguir." -ForegroundColor Yellow
    }
} else {
    Write-Host "      AVISO: falta docker-compose.airflow.yml" -ForegroundColor Yellow
}
$null = Wait-Puerto 8080 "Airflow UI" 120

# --- 4. Resumen URLs ---
Write-Host "[4/5] URLs del stack..." -ForegroundColor Cyan
Write-Host ""
Write-Host "  App DiabCare   http://localhost:8000" -ForegroundColor White
Write-Host "  API / docs     http://localhost:8000/docs" -ForegroundColor White
Write-Host "  MinIO          http://localhost:9001" -ForegroundColor White
Write-Host "  PocketBase     http://localhost:8090/_/" -ForegroundColor White
Write-Host "  Airflow        http://localhost:8080   (admin / admin)" -ForegroundColor White
Write-Host ""
Write-Host '  DAGs: diabcare_elt (hourly E-L-T) | diabcare_elt_historico | diabcare_benchmark_sql' -ForegroundColor DarkGray
Write-Host '  UI:   Datos -> Orquestador  |  carpeta etl/ + dags/' -ForegroundColor DarkGray
Write-Host ""

# --- 5. Backend FastAPI ---
Write-Host "[5/5] Backend FastAPI..." -ForegroundColor Cyan
$env:PYTHONPATH = "$PSScriptRoot;$PSScriptRoot\backend"

if (Test-Puerto 8000) {
    Write-Host "      Ya habia un proceso en :8000. Stack listo (no se relanzo el backend)." -ForegroundColor Green
    Write-Host "      Si cambiaste codigo, detener con .\detener.ps1 y vuelve a arrancar." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Listo. Abre http://localhost:8000" -ForegroundColor Green
    exit 0
}

Write-Host "      Arrancando servidor (Ctrl+C detiene solo el backend)..." -ForegroundColor Green
Write-Host ""
py -3 "$PSScriptRoot\servidor.py"