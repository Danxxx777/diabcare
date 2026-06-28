# Modelo de Datos (Fase 1): P7 — Reportes PDF

**Fecha**: 2026-06-19

Las entidades describen el contenido lógico del reporte y su metadato de
almacenamiento. No se crean nuevas tablas en el DWH; los reportes se persisten
como objetos PDF en MinIO.

## Entidad: Reporte

Representa un reporte generado y almacenado.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| nombre | string | Nombre del archivo: `reporte_{timestamp}.pdf` |
| ruta | string | Ruta en MinIO: `reportes/{nombre}` (bucket `diabcare-app`) |
| fecha_generacion | datetime | Fecha y hora de creación |
| usuario | string | Email/identificador del solicitante (del token JWT) |
| tamano_bytes | int | Tamaño del archivo |
| filtros | objeto | Filtros aplicados (puede ser vacío) |

Reglas de validación:
- `nombre` único por timestamp; no se sobrescriben reportes de otros usuarios.
- `usuario` se deriva del token, no del cliente.

## Entidad: FiltroReporte (entrada, opcional)

| Campo | Tipo | Valores | Descripción |
|-------|------|---------|-------------|
| year | int? | p. ej. 2025 | Año del registro |
| location | string? | — | Ubicación |
| diabetes | int? | 0 / 1 | Diagnóstico |
| gender | string? | — | Género |
| age_min | float? | ≥ 0 | Edad mínima |
| age_max | float? | ≥ age_min | Edad máxima |

Validación: `age_max ≥ age_min`; combinaciones inválidas → 400 (RF-O-P07... /
RN). Si no hay filtros, el reporte cubre el conjunto completo.

## Sección lógica: Estadísticas del dataset

Derivada de `estadisticas_endpoint.estadisticas()` y/o
`GET /api/dataset/estadisticas`. Contiene:

| Dato | Origen |
|------|--------|
| total de registros | `estadisticas.total` / dataset |
| con/sin diabetes | conteos |
| promedio BMI (con/sin) | `promedios.bmi` |
| promedio HbA1c (con/sin) | `promedios.hba1c` |
| promedio glucosa (con/sin) | `promedios.glucosa` |
| distribución por género | `genero_counts` |
| top ubicaciones | `top_ubicaciones` |

## Sección lógica: Métricas del modelo

Derivada de `PrediccionServicio.obtener_metricas()`:

| Dato | Campo |
|------|-------|
| exactitud | `accuracy` |
| precisión | `precision` |
| sensibilidad (recall) | `recall` |
| F1 | `f1` |
| registros entrenamiento/prueba | `registros_entrenamiento`, `registros_prueba` |

Si `obtener_metricas()` devuelve error (modelo no entrenado), la sección indica
"Métricas del modelo no disponibles".

## Sección lógica: Resumen de registros filtrados

Derivada de `RegistrosClinicosServicio.buscar(filtros)`:

| Dato | Descripción |
|------|-------------|
| cantidad coincidente | número de registros del subconjunto |
| distribución por diagnóstico | con/sin diabetes en el subconjunto |
| promedios clínicos del subconjunto | BMI, HbA1c, glucosa (agregados) |

Si no hay coincidencias: texto "Sin registros para los filtros aplicados"
(RN-O-P07-002). Nunca se listan filas individuales (RNF-O-P07-002).

## Metadato de almacenamiento

- Bucket: `diabcare-app`
- Prefijo: `reportes/`
- Formato de nombre: `reporte_AAAAMMDD_HHMMSS.pdf`
