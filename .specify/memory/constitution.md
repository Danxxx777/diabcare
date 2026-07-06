# Constitución de DiabCare Analytics

Plataforma SaaS de análisis clínico de datos de diabetes hospitalaria. Esta
constitución define los principios, estándares y reglas de gobernanza que rigen
todo el desarrollo del sistema bajo la metodología Spec-Driven Development (SDD).

**Versión**: 1.1.0 | **Ratificada**: 2026-06-13 | **Última enmienda**: 2026-06-19

## Principios Fundamentales

### I. Desarrollo Guiado por Especificación (SDD)

No se programa lo que no está especificado. Toda funcionalidad DEBE recorrer el
flujo de especificación antes de implementarse. Cada endpoint de la API pública
DEBE definirse en un contrato OpenAPI 3.0 antes de implementarse.

### II. Arquitectura por Paquetes

Las funcionalidades DEBEN organizarse dentro de los 15 paquetes funcionales
(P1–P15): `backend/paquetes/`, `backend/nucleo/`, `frontend/paginas/{departamento}/`.

### III. Integridad del Data Warehouse

Los datos clínicos DEBEN seguir el modelo Hecho-Dimensión. El flujo ELT
(PocketBase → Airflow → Parquet/MinIO → FastAPI → Frontend) NO DEBE omitirse
para lecturas analíticas.

### IV. Calidad con Pruebas Primero

Las pruebas automatizadas DEBEN existir bajo `pruebas/` (pytest). Los endpoints
nuevos DEBEN tener pruebas de API.

### V. Seguridad y Cumplimiento de Datos Clínicos

Autenticación JWT (HS256) con control por roles. Operaciones sensibles DEBEN
generar auditoría.

### VI. Trazabilidad Empresarial

Toda funcionalidad DEBE ser trazable: OE → OT → OO → Departamento → Paquete →
CU → Historia de usuario. Especificaciones bajo `specs/`.

## Niveles Empresariales

| Nivel | Carpeta de specs |
|-------|------------------|
| General | `specs/000-sistema-general/` |
| Operativo | `specs/003-operativo/` |

## Stack

Python 3 + FastAPI · Vanilla JS · MinIO/Parquet · Airflow · scikit-learn
