# Especificación de Paquete: P4 — Dataset y Datos Sintéticos

**Nivel**: Operativo · **Departamento**: Datos e Ingeniería · **Paquete**: P4

**Caso de uso operativo**: CU-O05 (Generar datos sintéticos configurables) · OO5.4.1

**Estado**: Implementado

**Creado**: 2026-06-19

**Rutas reales**: `backend/api/dataset/DatasetRutas.py`,
`backend/servicios/dataset/DatasetServicio.py`,
`backend/servicios/dataset/DatasetGenerador.py`,
`frontend/paginas/dataset/index.html`

## 1. Objetivo

Permitir generar datos clínicos sintéticos configurables y exponer los hechos y
dimensiones del Data Warehouse para su consulta.

## 2. Contexto

Provee los datos que alimentan análisis (P5) y predicción (P6). Los datos se
almacenan como Parquet en MinIO siguiendo el modelo Hecho-Dimensión.

## 3. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Analista | `analista` | Generar dataset, consultar hechos/dimensiones |
| Administrador | `administrador` | Acceso total |

Acceso: `PERMISOS_MODULOS["dataset"] = ["administrador", "analista"]`.

## 4. Requisitos funcionales

- **RF-O-P04-001** (CU-O05): El sistema DEBE generar datos sintéticos
  configurables (cantidad, año) y cargarlos. *Real*: `POST /api/dataset/generar`.
- **RF-O-P04-002**: El sistema DEBE listar hechos con conteo total eficiente
  (metadata Parquet). *Real*: `GET /api/dataset/hechos`.
- **RF-O-P04-003**: El sistema DEBE exponer las dimensiones (paciente, ubicación,
  raza, condición). *Real*: `GET /api/dataset/dimension/{paciente|ubicacion|raza|condicion}`.
- **RF-O-P04-004**: El sistema DEBE exponer estadísticas del dataset (total, con
  y sin diabetes, columnas). *Real*: `GET /api/dataset/estadisticas`.

## 5. Requisitos no funcionales

- **RNF-O-P04-001**: El acceso exige rol `analista` o `administrador`.
- **RNF-O-P04-002**: El conteo de registros usa metadata Parquet (pyarrow) sin
  cargar todo en memoria.

## 6. Reglas de negocio

- **RN-O-P04-001**: Los datos sintéticos usan las columnas del modelo de datos.
- **RN-O-P04-002**: Las dimensiones se derivan del stage si no existen
  precalculadas.

## 7. Entradas

- Generación: cantidad (por defecto 100000), year (por defecto 2025).
- Paginación: skip, limit.

## 8. Salidas

- Resultado de generación (archivo Parquet en MinIO).
- Listados de hechos y dimensiones, estadísticas del dataset.

## 9. Escenarios

### Escenario 1: Generar dataset
- **Dado** un analista autenticado,
- **Cuando** solicita generar N registros para un año,
- **Entonces** el sistema crea y almacena el Parquet y queda disponible.

### Escenario 2: Consultar estadísticas
- **Dado** datos cargados,
- **Cuando** consulta `GET /api/dataset/estadisticas`,
- **Entonces** recibe el total real y el desglose con/sin diabetes.

## 10. Criterios de aceptación

- **CA-O-P04-001**: La generación crea datos consultables.
- **CA-O-P04-002**: El total reportado coincide con los Parquet del stage.
- **CA-O-P04-003**: Un rol sin permiso recibe 403.

## 11. Dependencias

- P1 (sesión y rol). MinIO/Parquet como almacenamiento.

## 12. Restricciones y fuera de alcance

- Fuera de alcance: importación de datasets clínicos externos reales y
  anonimización avanzada.
