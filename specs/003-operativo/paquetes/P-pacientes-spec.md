# Especificación de Paquete: Pacientes / HCE

**Nivel**: Operativo · **Departamento**: Operaciones Clínicas

**Caso de uso operativo**: CU-O17 (Expediente paciente HCE) · OO5.2.1

**Estado**: Implementado · **Actualizado**: 2026-07-05

**Rutas**: `backend/paquetes/clinico/pacientes/`, `frontend/paginas/clinico/pacientes/`

## 1. Objetivo

Gestionar el expediente clínico del paciente (Historia Clínica Electrónica): datos demográficos, foto, sede y estado.

## 2. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Administrador | `administrador` | CRUD pacientes, foto |
| Médico | `medico` | Consultar y editar expedientes |

Acceso: `PERMISOS_MODULOS["pacientes"] = ["administrador", "medico"]`.

## 3. Requisitos funcionales

- **RF-O-PAC-001**: CRUD de pacientes. *Real*: `/api/pacientes/`
- **RF-O-PAC-002**: Resumen total/activos/inactivos. *Real*: `GET /api/pacientes/resumen`
- **RF-O-PAC-003**: Búsqueda por nombre, documento, código. *Real*: query `q`
- **RF-O-PAC-004**: Foto del paciente (MinIO + `oper_fotos_entidad.parquet`). *Real*: `GET/POST /api/pacientes/{id}/foto`
- **RF-O-PAC-005**: Miniatura en tabla + visor ampliado al clic.

## 4. Reglas de negocio

- **RN-O-PAC-001**: Documento único por paciente activo.
- **RN-O-PAC-002**: Foto máx. 5 MB (JPEG, PNG, WebP).

## 5. Criterios de aceptación

- **CA-O-PAC-001**: Admin crea paciente y sube foto; aparece en tabla sin recargar manualmente.
- **CA-O-PAC-002**: Clic en miniatura abre visor con nombre del paciente.
