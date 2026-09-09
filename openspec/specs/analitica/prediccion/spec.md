# P6 - Predicción ML Specification

## Purpose

Predecir el riesgo de diabetes de un paciente a partir de variables clínicas y exponer las métricas de desempeño del modelo.

## Requirements

### Requirement: RF-O-P06-001

(CU-O08): El sistema SHALL predecir el riesgo de diabetes a partir de age, bmi, hbA1c_level, blood_glucose_level, hypertension, heart_disease, devolviendo el diagnóstico estimado y probabilidad.

#### Scenario: Cumplimiento de RF-O-P06-001
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/prediccion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P06-001`

### Requirement: RF-O-P06-002

(CU-O09): El sistema SHALL exponer las métricas del modelo.

#### Scenario: Cumplimiento de RF-O-P06-002
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/prediccion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P06-002`

### Requirement: RF-O-P06-003

El sistema SHALL permitir entrenar el modelo.

#### Scenario: Cumplimiento de RF-O-P06-003
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/prediccion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P06-003`

### Requirement: RF-O-P06-004

El sistema SHALL informar si el modelo está disponible.

#### Scenario: Cumplimiento de RF-O-P06-004
- **WHEN** un usuario autorizado utiliza la capacidad `analitica/prediccion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P06-004`
