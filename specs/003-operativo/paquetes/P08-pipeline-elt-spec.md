# Especificación de Paquete: P8 — Pipeline ELT

**Nivel**: Operativo · **Departamento**: Datos e Ingeniería · **Paquete**: P8

**Caso de uso operativo**: CU-O06 (Ejecutar pipeline ELT) · OO5.3.1

**Estado**: Implementado (consulta + pasos E·T·L + DAGs Airflow + benchmark SQL)

**Creado**: 2026-06-19 · **Actualizado**: 2026-08-11

> **Identificador técnico en código**: carpetas y permisos usan `pipeline_etl`
> (compatibilidad P8). La nomenclatura funcional y de documentación es
> **Pipeline ELT** (Extract → Load → Transform). Orden en código y DAGs: **E→L→T**.

**Rutas reales**:
- Proceso: `etl/` (`extract.py`, `load.py`, `transform.py`, `benchmark_sql.py`)
- API: `backend/paquetes/pipeline_elt/`
- UI: `frontend/paginas/datos/pipeline_elt/index.html`
- Orquestación: `dags/diabcare_elt.py`, `diabcare_elt_historico.py`, `diabcare_benchmark_sql.py`

## 1. Objetivo

Ejecutar y supervisar el pipeline **ELT** (PocketBase → Airflow → landing MinIO →
transformación en stage/DWH), medir duraciones y comparar informe SQL vs columnar.

## 2. Orden ELT (no ETL)

| Paso | Qué hace | Destino |
|------|----------|---------|
| **E** Extraer | Lee PocketBase (incremental o histórico) | work temporal |
| **L** Cargar | Sube **crudo** al almacén | `diabetes-data/landing/` |
| **T** Transformar | Normaliza + Hecho-Dim | `stage/` + DWH |

Landing está **fuera** de `stage/` para no mezclar crudo con lecturas clínicas.

## 3. DAGs (hoja de ruta)

| DAG | Schedule | Modo |
|-----|----------|------|
| `diabcare_elt` | `@hourly` | Incremental E→L→T |
| `diabcare_elt_historico` | `0 3 * * 0` | Histórico E→L→T |
| `diabcare_benchmark_sql` | `@daily` | SQL vs Parquet |

Estrategia: **incremental** (no borrar landing/stage). Histórico añade Parquet y rematerializa DWH.

## 4. Requisitos

- **RF-O-P08-001**: Consultar estado (`GET /api/pipeline/estado`).
- **RF-O-P08-002**: Ejecutar ELT orquestado por Airflow (DAGs en `dags/`).
- **RF-O-P08-003**: Pasos internos `extraer` → `cargar` → `transformar`.
- **RF-O-P08-004**: Benchmark SQL tradicional vs Parquet.
- **RNF-O-P08-002**: Meta ELT 600K &lt; 15 min; duración en UI.

## 5. Compatibilidad SQL / PocketBase

- Benchmark: SQLite 3 + SQL ANSI.
- Extracción PB: fallback filtro local si el filtro `updated` falla.

## 6. OE / dashboards / IA

| OE | Dashboard / módulo | IA |
|----|--------------------|-----|
| OE4 BI | Estadísticas, Análisis, KPIs, Reportes | — |
| OE4 ML | Predicción, Modelo ML | **Random Forest** (OO5.6.1) |
| OE1–OE3 | Fuera demo GA07 | No requiere IA |

## 7. Criterios de aceptación

- CA: DAGs en orden E→L→T en Airflow.
- CA: Crudo en `landing/`; limpio en `stage/`.
- CA: Benchmark con `tiempos_ms`.
- CA: Duraciones E/L/T visibles en UI.
