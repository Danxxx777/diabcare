# Especificación de Paquete: Admisiones hospitalarias

**Nivel**: Operativo · **Departamento**: Operaciones Clínicas

**Caso de uso operativo**: CU-O19 (Registrar admisión) · OO5.2.1

**Estado**: Implementado · **Actualizado**: 2026-07-05

**Rutas**: `backend/paquetes/clinico/admisiones/`, `frontend/paginas/clinico/admisiones/`

## 1. Objetivo

Registrar ingresos hospitalarios (ambulatoria, urgencia, hospitalización) asignando médico tratante.

## 2. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Administrador | `administrador` | Crear, editar, listar admisiones |

Acceso: `PERMISOS_MODULOS["admisiones"] = ["administrador"]`.

## 3. Requisitos funcionales

- **RF-O-ADM-001**: CRUD admisiones. *Real*: `/api/admisiones/`
- **RF-O-ADM-002**: Resumen total/activas/altas. *Real*: `GET /api/admisiones/resumen`
- **RF-O-ADM-003**: Selector de paciente registrado.
- **RF-O-ADM-004**: Selector de **médico tratante** desde usuarios activos rol `medico`. *Real*: `GET /api/usuarios/medicos`

## 4. Reglas de negocio

- **RN-O-ADM-001**: Solo administración registra admisiones (no el médico).
- **RN-O-ADM-002**: `medico_nombre` debe coincidir con el nombre del usuario médico en P2.

## 5. Criterios de aceptación

- **CA-O-ADM-001**: Admin crea admisión con paciente y médico del dropdown.
- **CA-O-ADM-002**: Médico no ve el módulo Admisiones en el menú.
