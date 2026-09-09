# RRHH clínico y costeo Specification

## Purpose

Implementar RRHH clínico y costeo con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

## Requirements

### Requirement: Comportamiento de RRHH clínico y costeo

El sistema SHALL implementar RRHH clínico y costeo con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

#### Scenario: Cumplimiento de Comportamiento de RRHH clínico y costeo
- **WHEN** un usuario autorizado utiliza la capacidad `negocio/rrhh-costeo`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `Comportamiento de RRHH clínico y costeo`
