# P5 - Análisis y Visualización Specification

## Purpose

Presentar estadísticas clínicas (prevalencia, promedios, distribuciones, comorbilidades, tendencias) de forma visual con gráficas para apoyar el análisis.

## Requirements

### Requirement: RF-O-P05-001

(CU-O07): El sistema SHALL calcular estadísticas clínicas: totales, distribución por género, tabaquismo vs diabetes, raza, rangos de edad, promedios clínicos (BMI, HbA1c, glucosa), comorbilidades y top de ubicaciones.

#### Scenario: Cumplimiento de RF-O-P05-001
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/analisis`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P05-001`

### Requirement: RF-O-P05-002

El sistema SHALL exponer estadísticas agregadas del dataset.

#### Scenario: Cumplimiento de RF-O-P05-002
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/analisis`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P05-002`

### Requirement: RF-O-P05-003

El frontend SHALL visualizar las estadísticas con gráficas.

#### Scenario: Cumplimiento de RF-O-P05-003
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/analisis`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P05-003`
