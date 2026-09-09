# P8 - Pipeline ELT Specification

## Purpose

Ejecutar y supervisar el pipeline **ELT** (PocketBase → Airflow → landing MinIO → transformación en stage/DWH), medir duraciones y comparar informe SQL vs columnar.

## Requirements

### Requirement: RF-O-P08-001

Consultar estado (`GET /api/pipeline/estado`).

#### Scenario: Cumplimiento de RF-O-P08-001
- **WHEN** un usuario autorizado utiliza la capacidad `datos/pipeline-elt`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P08-001`

### Requirement: RF-O-P08-002

Ejecutar ELT orquestado por Airflow (DAGs en `dags/`).

#### Scenario: Cumplimiento de RF-O-P08-002
- **WHEN** un usuario autorizado utiliza la capacidad `datos/pipeline-elt`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P08-002`

### Requirement: RF-O-P08-003

Pasos internos `extraer` → `cargar` → `transformar`.

#### Scenario: Cumplimiento de RF-O-P08-003
- **WHEN** un usuario autorizado utiliza la capacidad `datos/pipeline-elt`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P08-003`

### Requirement: RF-O-P08-004

Benchmark SQL tradicional vs Parquet.

#### Scenario: Cumplimiento de RF-O-P08-004
- **WHEN** un usuario autorizado utiliza la capacidad `datos/pipeline-elt`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P08-004`

### Requirement: RNF-O-P08-002

Meta ELT 600K &lt; 15 min; duración en UI.

#### Scenario: Cumplimiento de RNF-O-P08-002
- **WHEN** un usuario autorizado utiliza la capacidad `datos/pipeline-elt`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RNF-O-P08-002`
