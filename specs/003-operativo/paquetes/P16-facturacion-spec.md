# Especificación de Paquete: Facturación

**Nivel**: Operativo · **Departamento**: Operaciones clínicas / Negocio hospitalario
**Caso de uso**: CU-O21 · **Estado**: Implementado (DiabCare Hospital)
**Fuente**: Especificación maestra consolidada DiabCare Hospital

## Objetivo
Implementar Facturación con CRUD completo (C/R/U/D lógico), roles ampliados y tablas Parquet en MinIO, sin modificar el core de 59 tablas clínicas. FKs vía `encounter_id` / `id_paciente`.

## Reglas
- RN-CRUD-001: DELETE siempre lógico (`estado=anulado/anulada` o `activo=false`) y auditado.
- Core intocable; lecturas analíticas desde Parquet materializado cuando aplique.

## Backend
`backend/paquetes/` · Frontend `frontend/paginas/`
