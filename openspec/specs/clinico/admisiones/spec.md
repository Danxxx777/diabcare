# Admisiones hospitalarias Specification

## Purpose

Registrar ingresos hospitalarios (ambulatoria, urgencia, hospitalización) asignando médico tratante.

## Requirements

### Requirement: RF-O-ADM-001

CRUD admisiones.

#### Scenario: Cumplimiento de RF-O-ADM-001
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/admisiones`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-ADM-001`

### Requirement: RF-O-ADM-002

Resumen total/activas/altas.

#### Scenario: Cumplimiento de RF-O-ADM-002
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/admisiones`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-ADM-002`

### Requirement: RF-O-ADM-003

Selector de paciente registrado.

#### Scenario: Cumplimiento de RF-O-ADM-003
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/admisiones`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-ADM-003`

### Requirement: RF-O-ADM-004

Selector de **médico tratante** desde usuarios activos rol `medico`.

#### Scenario: Cumplimiento de RF-O-ADM-004
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/admisiones`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-ADM-004`
