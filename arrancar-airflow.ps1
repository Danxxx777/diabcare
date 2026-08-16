# Arranca Apache Airflow (orquestador ELT DiabCare)
# UI: http://localhost:8080  (admin / admin)
# Requiere Docker Desktop. El backend debe estar en :8000.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Levantando Airflow (webserver + scheduler)..." -ForegroundColor Cyan
docker compose -f docker-compose.airflow.yml up -d

Write-Host ""
Write-Host "Airflow UI : http://localhost:8080" -ForegroundColor Green
Write-Host "Usuario    : admin / admin" -ForegroundColor Green
Write-Host "DAGs       :" -ForegroundColor Green
Write-Host "  - diabcare_elt            @hourly     (E->L->T incremental)" -ForegroundColor Green
Write-Host "  - diabcare_elt_historico   0 3 * * 0   (historico domingo)" -ForegroundColor Green
Write-Host "  - diabcare_benchmark_sql   @daily      (SQL vs Parquet)" -ForegroundColor Green
Write-Host ""
Write-Host "Carpeta ETL: .\etl\  |  DAGs: .\dags\" -ForegroundColor Yellow
Write-Host "En DiabCare: Datos -> Orquestador (elige DAG + benchmark)" -ForegroundColor Yellow
Write-Host "Si el iframe no carga, reinicie Airflow tras actualizar docker-compose" -ForegroundColor DarkYellow

