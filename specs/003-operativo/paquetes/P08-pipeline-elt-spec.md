# Especificación de Paquete: P8 — Pipeline ELT

**Nivel**: Operativo · **Departamento**: Datos e Ingeniería · **Paquete**: P8

**Caso de uso operativo**: CU-O06 (Ejecutar pipeline ELT) · OO5.3.1

**Estado**: Parcial (consulta de estado implementada; ejecución orquestada pendiente)

**Creado**: 2026-06-19

> **Identificador técnico en código**: carpetas y permisos usan `pipeline_etl`
> (compatibilidad P8). La nomenclatura funcional y de documentación es
> **Pipeline ELT** (Extract → Load → Transform).

**Rutas reales**: `backend/paquetes/pipeline_elt/PipelineEtlRutas.py`,
`backend/paquetes/pipeline_elt/PipelineEtlServicio.py`,
`frontend/paginas/datos/pipeline_elt/index.html`. Orquestación prevista con
Apache Airflow (`dags/`).

## 1. Objetivo

Ejecutar y supervisar el pipeline ELT que carga datos al Data Warehouse
(PocketBase → Airflow → Parquet/MinIO), y consultar su estado.

## 2. Contexto

P8 mantiene el DWH actualizado. Actualmente está implementada la consulta de
estado (archivos en stage, fechas, tamaños); la ejecución orquestada por Airflow
es la parte pendiente.

## 3. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Analista | `analista` | Consultar estado del pipeline |
| Administrador | `administrador` | Acceso total |
| Sistema (Airflow) | proceso | Ejecutar el ELT automatizado |

Acceso: `PERMISOS_MODULOS["pipeline_etl"] = ["administrador", "analista"]`.

## 4. Requisitos funcionales

- **RF-O-P08-001** (CU-O06): El sistema DEBE permitir consultar el estado del
  pipeline (estado, bucket, total de archivos, último archivo y fecha, listado
  reciente). *Real*: `GET /api/pipeline/estado`.
- **RF-O-P08-002** (CU-O06): El sistema DEBE ejecutar el pipeline ELT sin
  intervención manual (orquestado por Airflow). *Pendiente* — DAGs en `dags/`.

## 5. Requisitos no funcionales

- **RNF-O-P08-001**: El acceso exige rol `analista` o `administrador`.
- **RNF-O-P08-002**: El ELT de 600K registros DEBE completarse en < 15 min (meta
  TA06).

## 6. Reglas de negocio

- **RN-O-P08-001**: Los datos cargados se almacenan como Parquet en el prefijo
  stage del bucket.
- **RN-O-P08-002**: La consulta de estado reporta los archivos más recientes.

## 7. Entradas

- Token de sesión. (La ejecución programada no requiere entrada de usuario.)

## 8. Salidas

- Estado del pipeline: bucket, prefijo, total de archivos, último archivo, fecha
  y listado reciente.

## 9. Escenarios

### Escenario 1: Consultar estado del pipeline
- **Dado** un analista autenticado,
- **Cuando** consulta `GET /api/pipeline/estado`,
- **Entonces** recibe el estado y los archivos recientes del stage.

### Escenario 2: Sin conexión al almacenamiento
- **Dado** un fallo de conexión a MinIO,
- **Cuando** consulta el estado,
- **Entonces** el sistema responde con estado "error" y el detalle.

## 10. Criterios de aceptación

- **CA-O-P08-001**: La consulta de estado lista los Parquet del stage.
- **CA-O-P08-002**: Ante error de almacenamiento, la respuesta indica "error".
- **CA-O-P08-003**: Un rol sin permiso recibe 403.

## 11. Dependencias

- P1 (sesión y rol), MinIO/Parquet, Apache Airflow (orquestación).

## 12. Restricciones y fuera de alcance

- Fuera de alcance en esta iteración: disparo manual del DAG desde la UI y
  reprocesos selectivos; se documentará al implementar la orquestación.
