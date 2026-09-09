# Pacientes / HCE Specification

## Purpose

Gestionar el expediente clínico del paciente (Historia Clínica Electrónica): datos demográficos, foto, sede y estado.

## Requirements

### Requirement: RF-O-PAC-001

CRUD de pacientes.

#### Scenario: Cumplimiento de RF-O-PAC-001
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/pacientes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-PAC-001`

### Requirement: RF-O-PAC-002

Resumen total/activos/inactivos.

#### Scenario: Cumplimiento de RF-O-PAC-002
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/pacientes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-PAC-002`

### Requirement: RF-O-PAC-003

Búsqueda por nombre, documento, código.

#### Scenario: Cumplimiento de RF-O-PAC-003
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/pacientes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-PAC-003`

### Requirement: RF-O-PAC-004

Foto del paciente (MinIO + `oper_fotos_entidad.parquet`).

#### Scenario: Cumplimiento de RF-O-PAC-004
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/pacientes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-PAC-004`

### Requirement: RF-O-PAC-005

Miniatura en tabla + visor ampliado al clic.

#### Scenario: Cumplimiento de RF-O-PAC-005
- **WHEN** un usuario autorizado utiliza la capacidad `clinico/pacientes`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-PAC-005`
