# P4 - Dataset y Datos Sintéticos Specification

## Purpose

Permitir generar datos clínicos sintéticos configurables y exponer los hechos y dimensiones del Data Warehouse para su consulta.

## Requirements

### Requirement: RF-O-P04-001

(CU-O05): El sistema SHALL generar datos sintéticos configurables (cantidad, año) y cargarlos.

#### Scenario: Cumplimiento de RF-O-P04-001
- **WHEN** un usuario autorizado utiliza la capacidad `datos/dataset`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P04-001`

### Requirement: RF-O-P04-002

El sistema SHALL listar hechos con conteo total eficiente (metadata Parquet).

#### Scenario: Cumplimiento de RF-O-P04-002
- **WHEN** un usuario autorizado utiliza la capacidad `datos/dataset`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P04-002`

### Requirement: RF-O-P04-003

El sistema SHALL exponer las dimensiones (paciente, ubicación, raza, condición).

#### Scenario: Cumplimiento de RF-O-P04-003
- **WHEN** un usuario autorizado utiliza la capacidad `datos/dataset`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P04-003`

### Requirement: RF-O-P04-004

El sistema SHALL exponer estadísticas del dataset (total, con y sin diabetes, columnas).

#### Scenario: Cumplimiento de RF-O-P04-004
- **WHEN** un usuario autorizado utiliza la capacidad `datos/dataset`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P04-004`
