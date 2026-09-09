# P12 - Configuración del Sistema Specification

## Purpose

Permitir al administrador consultar y ajustar parámetros del sistema (MinIO, umbrales clínicos, preferencias) sin modificar código.

## Requirements

### Requirement: RF-O-P12-001

Obtener configuración actual.

#### Scenario: Cumplimiento de RF-O-P12-001
- **WHEN** un usuario autorizado utiliza la capacidad `gobierno/configuracion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P12-001`

### Requirement: RF-O-P12-002

Persistir cambios con auditoría.

#### Scenario: Cumplimiento de RF-O-P12-002
- **WHEN** un usuario autorizado utiliza la capacidad `gobierno/configuracion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P12-002`
