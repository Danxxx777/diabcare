# P1 - Autenticación y Seguridad Specification

## Purpose

Permitir que los usuarios accedan de forma segura al sistema mediante autenticación con token JWT y control de acceso por roles.

## Requirements

### Requirement: RF-O-P01-001

(CU-O01): El sistema SHALL autenticar con email y contraseña y emitir un token JWT (HS256) con el rol.

#### Scenario: Cumplimiento de RF-O-P01-001
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/autenticacion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P01-001`

### Requirement: RF-O-P01-002

El sistema SHALL verificar la validez de un token.

#### Scenario: Cumplimiento de RF-O-P01-002
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/autenticacion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P01-002`

### Requirement: RF-O-P01-003

El sistema SHALL permitir cerrar sesión.

#### Scenario: Cumplimiento de RF-O-P01-003
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/autenticacion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P01-003`

### Requirement: RF-O-P01-004

El sistema SHALL permitir recuperar contraseña mediante código.

#### Scenario: Cumplimiento de RF-O-P01-004
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/autenticacion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P01-004`

### Requirement: RF-O-P01-005

El sistema SHALL permitir cambiar la contraseña autenticado.

#### Scenario: Cumplimiento de RF-O-P01-005
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/autenticacion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P01-005`

### Requirement: RF-O-P01-007

Al aprobar acceso, el sistema SHALL emitir credenciales temporales y exigir cambio de contraseña en el primer acceso (`debe_cambiar_password`).

#### Scenario: Cumplimiento de RF-O-P01-007
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/autenticacion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P01-007`

### Requirement: RF-O-P01-008

El sistema SHALL registrar sesiones JWT (`jti`) con revocación y límite de concurrencia (máx. 5). `GET/DELETE /api/auth/sesiones` (admin).

#### Scenario: Cumplimiento de RF-O-P01-008
- **WHEN** un usuario autorizado utiliza la capacidad `seguridad/autenticacion`
- **THEN** el sistema SHALL cumplir el comportamiento definido en `RF-O-P01-008`
