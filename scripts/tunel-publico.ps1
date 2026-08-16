# DiabCare — túnel público para QR (informes y cobro de consulta)
#
# El QR apunta a DIABCARE_PUBLIC_URL. Sin túnel, usa la IP de tu Wi‑Fi y
# solo funciona en la misma red. Con este script, cualquiera con datos
# móviles puede escanear.
#
# Requisitos:
#   1. Backend en http://127.0.0.1:8000  (.\arrancar.ps1)
#   2. cloudflared:  winget install Cloudflare.cloudflared
#
# Deja esta ventana abierta. Ctrl+C cierra el túnel.

$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cf) {
    Write-Host "No está cloudflared. Instálalo con:" -ForegroundColor Yellow
    Write-Host "  winget install Cloudflare.cloudflared"
    Write-Host "Luego vuelve a ejecutar: .\scripts\tunel-publico.ps1"
    exit 1
}

Write-Host "Abriendo túnel hacia http://127.0.0.1:8000 …" -ForegroundColor Cyan
Write-Host "Cuando aparezca https://….trycloudflare.com se guardará en .env"
Write-Host "Pégala también en Configuración → Sistema → URL pública (no hace falta reiniciar)."
Write-Host ""

$envPath = Join-Path (Get-Location) ".env"
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $cf.Source
$psi.Arguments = "tunnel --url http://127.0.0.1:8000"
$psi.RedirectStandardError = $true
$psi.RedirectStandardOutput = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$p = [System.Diagnostics.Process]::Start($psi)

function Save-PublicUrl([string]$url) {
    $url = $url.Trim().TrimEnd("/")
    if (-not $url) { return }
    Write-Host ""
    Write-Host "URL pública: $url" -ForegroundColor Green
    if (Test-Path $envPath) {
        $raw = Get-Content $envPath -Raw -Encoding UTF8
        if ($raw -match "(?m)^DIABCARE_PUBLIC_URL=") {
            $raw = [regex]::Replace($raw, "(?m)^DIABCARE_PUBLIC_URL=.*$", "DIABCARE_PUBLIC_URL=$url")
        } else {
            $raw = $raw.TrimEnd() + "`r`nDIABCARE_PUBLIC_URL=$url`r`n"
        }
        Set-Content -Path $envPath -Value $raw -Encoding UTF8 -NoNewline
        Write-Host "Actualizado DIABCARE_PUBLIC_URL en .env (reinicia el backend para leerlo," -ForegroundColor Yellow
        Write-Host " o pégala ahora en Configuración → Sistema y Guardar)." -ForegroundColor Yellow
    } else {
        Write-Host "No hay .env. Copia .env.example o pega la URL en Configuración → Sistema." -ForegroundColor Yellow
    }
    Write-Host "Deja esta ventana abierta. Ctrl+C para cerrar el túnel."
}

$found = $false
try {
    while (-not $p.HasExited) {
        $line = $p.StandardError.ReadLine()
        if ($null -eq $line) { Start-Sleep -Milliseconds 200; continue }
        Write-Host $line
        if (-not $found -and $line -match "https://[a-z0-9-]+\.trycloudflare\.com") {
            $found = $true
            Save-PublicUrl $Matches[0]
        }
    }
} finally {
    if (-not $p.HasExited) { $p.Kill() }
}
