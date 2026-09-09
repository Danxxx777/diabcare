# Comorbilidades del paciente (extensión P3) Specification

## Purpose

Implementar Comorbilidades del paciente (extensión P3) con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

## Requirements

### Requirement: Comportamiento de Comorbilidades del paciente (extensión P3)

El sistema SHALL implementar Comorbilidades del paciente (extensión P3) con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

#### Scenario: Cumplimiento de Comportamiento de Comorbilidades del paciente (extensión P3)
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/comorbilidades`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `Comportamiento de Comorbilidades del paciente (extensión P3)`
