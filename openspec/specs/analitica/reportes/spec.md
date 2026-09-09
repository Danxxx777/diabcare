# P7 - Reportes Specification

## Purpose

Permitir generar reportes clínicos descargables en PDF que resuman estadísticas del dataset, métricas del modelo de predicción y un resumen de registros filtrados, para compartir hallazgos fuera de la plataforma.

## Requirements

### Requirement: RF-O-P07-001

El sistema SHALL permitir a un usuario autorizado generar un reporte clínico en PDF.

#### Scenario: Cumplimiento de RF-O-P07-001
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/reportes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P07-001`

### Requirement: RF-O-P07-002

El reporte SHALL incluir estadísticas del dataset (total de registros, % con diabetes, promedios de BMI, HbA1c y glucosa, distribución por género).

#### Scenario: Cumplimiento de RF-O-P07-002
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/reportes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P07-002`

### Requirement: RF-O-P07-003

El reporte SHALL incluir métricas del modelo de predicción cuando exista evaluación vigente; si no, indicar que no están disponibles.

#### Scenario: Cumplimiento de RF-O-P07-003
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/reportes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P07-003`

### Requirement: RF-O-P07-004

El sistema SHALL aceptar filtros opcionales (año, ubicación, diabetes, género, rango de edad) y reflejar el subconjunto en un resumen.

#### Scenario: Cumplimiento de RF-O-P07-004
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/reportes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P07-004`

### Requirement: RF-O-P07-005

El sistema SHALL entregar el PDF en español, con fecha/hora de generación y usuario solicitante.

#### Scenario: Cumplimiento de RF-O-P07-005
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/reportes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P07-005`

### Requirement: RF-O-P07-006

El sistema SHALL listar los reportes generados (nombre, fecha, tamaño) y permitir su descarga posterior.

#### Scenario: Cumplimiento de RF-O-P07-006
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/reportes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P07-006`

### Requirement: RF-O-P07-007

El sistema SHALL registrar en auditoría cada generación y descarga de reporte.

#### Scenario: Cumplimiento de RF-O-P07-007
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/reportes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P07-007`
