# P2 - Gestión de Usuarios Specification

## Purpose

Permitir al administrador gestionar las cuentas de usuario del sistema: creación, consulta, edición, desactivación y asignación de roles.

## Requirements

### Requirement: RF-O-P02-001

(CU-O02): El administrador SHALL poder listar usuarios.

#### Scenario: Cumplimiento de RF-O-P02-001
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/usuarios`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P02-001`

### Requirement: RF-O-P02-002

El administrador SHALL poder consultar los roles válidos.

#### Scenario: Cumplimiento de RF-O-P02-002
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/usuarios`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P02-002`

### Requirement: RF-O-P02-003

El administrador SHALL poder obtener un usuario por id.

#### Scenario: Cumplimiento de RF-O-P02-003
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/usuarios`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P02-003`

### Requirement: RF-O-P02-004

El administrador SHALL poder crear un usuario con rol válido.

#### Scenario: Cumplimiento de RF-O-P02-004
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/usuarios`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P02-004`

### Requirement: RF-O-P02-005

El administrador SHALL poder editar un usuario.

#### Scenario: Cumplimiento de RF-O-P02-005
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/usuarios`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P02-005`

### Requirement: RF-O-P02-006

El administrador SHALL poder desactivar un usuario.

#### Scenario: Cumplimiento de RF-O-P02-006
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/usuarios`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P02-006`

### Requirement: RF-O-P02-007

El administrador SHALL poder asignar/cambiar el rol.

#### Scenario: Cumplimiento de RF-O-P02-007
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/usuarios`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P02-007`
