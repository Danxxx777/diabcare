# Farmacia (dispensación, compras, ventas, contabilidad) Specification

## Purpose

Implementar Farmacia (dispensación, compras, ventas, contabilidad) con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

## Requirements

### Requirement: Comportamiento de Farmacia (dispensación, compras, ventas, contabilidad)

El sistema SHALL implementar Farmacia (dispensación, compras, ventas, contabilidad) con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

#### Scenario: Cumplimiento de Comportamiento de Farmacia (dispensación, compras, ventas, contabilidad)
- **WHEN** un usuario autorizado utiliza la capacidad `negocio/farmacia`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `Comportamiento de Farmacia (dispensación, compras, ventas, contabilidad)`
