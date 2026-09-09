# Laboratorio clínico Specification

## Purpose

Implementar Laboratorio clínico con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

## Requirements

### Requirement: Comportamiento de Laboratorio clínico

El sistema SHALL implementar Laboratorio clínico con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

#### Scenario: Cumplimiento de Comportamiento de Laboratorio clínico
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/laboratorio`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `Comportamiento de Laboratorio clínico`
