# Urgencias / triage Specification

## Purpose

Implementar Urgencias / triage con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

## Requirements

### Requirement: Comportamiento de Urgencias / triage

El sistema SHALL implementar Urgencias / triage con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

#### Scenario: Cumplimiento de Comportamiento de Urgencias / triage
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/urgencias`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `Comportamiento de Urgencias / triage`
