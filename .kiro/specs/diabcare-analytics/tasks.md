# Tareas de Implementación — DiabCare Analytics

## Grafo de Dependencias de Tareas

```
Tarea 1 (Backend: conexión MinIO y get_df)
   Tarea 2 (Backend: /api/cargar-dataset)
   Tarea 3 (Backend: /api/stats)
   Tarea 4 (Backend: /api/tabla con TABLAS_MAP)
   Tarea 5 (Backend: CRUD /api/fact)
   Tarea 6 (Backend: charts)
   Tarea 7 (Backend: /api/empresa)
         Tarea 8 (Frontend: Dashboard)
         Tarea 9 (Frontend: Ver Tablas)
         Tarea 10 (Frontend: CRUD Fact)
         Tarea 11 (Frontend: Pipeline + recarga)
         Tarea 12 (Frontend: Empresa/Objetivos)
               Tarea 13 (PBT: Properties 1 y 2 — TABLAS_MAP)
               Tarea 14 (PBT: Property 3 — limit)
               Tarea 15 (PBT: Properties 4 y 5 — caché y tablas virtuales)
               Tarea 16 (PBT: Property 6 — stats)
               Tarea 17 (PBT: Property 7 — empresa)
               Tarea 18 (PBT: Properties 8 y 9 — charts)
               Tarea 19 (PBT: Properties 10 y 11 — CRUD)
               Tarea 20 (Integración y smoke tests)
```

---

## Tarea 1: Backend — Conexión MinIO y función `get_df`

- [ ] 1.1 Verificar que las constantes de conexión MinIO (`MINIO_ENDPOINT`, `MINIO_ACCESS`, `MINIO_SECRET`, `MINIO_BUCKET`, `MINIO_PREFIX`) están definidas al nivel de módulo en `main.py`.
- [ ] 1.2 Verificar que `get_minio_client()` retorna una instancia de `Minio` con `secure=False` y las credenciales configuradas (Requisito 1.2).
- [ ] 1.3 Verificar que `get_df()` lista los objetos del bucket con el prefijo `stage/`, filtra por extensión `.parquet`, selecciona el más reciente por `last_modified` y lo carga con `pd.read_parquet(BytesIO(...))` (Requisito 1.2).
- [ ] 1.4 Verificar que `get_df()` almacena el DataFrame en `_df_cache` y retorna la caché en llamadas posteriores sin volver a conectarse a MinIO (Requisito 1.3).
- [ ] 1.5 Verificar que `get_df()` lanza `HTTPException(404)` con el mensaje correcto cuando no hay objetos en `stage/` (Requisito 1.6).
- [ ] 1.6 Verificar que `get_df()` lanza `HTTPException(404)` con el mensaje correcto cuando no hay archivos `.parquet` (Requisito 1.7).

**Archivos afectados:** `backend/app/main.py`
**Valida:** Requisito 1.2, 1.3, 1.6, 1.7, 1.8, Property 4

---

## Tarea 2: Backend — Endpoint `POST /api/cargar-dataset`

- [ ] 2.1 Verificar que `POST /api/cargar-dataset` asigna `_df_cache = None` antes de invocar `get_df()` para forzar la descarga desde MinIO (Requisito 1.4).
- [ ] 2.2 Verificar que la respuesta exitosa contiene `ok: true`, `registros` (int con el número de filas) y `columnas` (lista de strings con los nombres de columna) (Requisito 1.5).
- [ ] 2.3 Verificar que si MinIO no está disponible, el endpoint propaga el error HTTP 500 con `detail` descriptivo (Requisito 1.8).

**Archivos afectados:** `backend/app/main.py`
**Valida:** Requisito 1.4, 1.5, 1.8

---

## Tarea 3: Backend — Endpoint `GET /api/stats`

- [ ] 3.1 Verificar que `/api/stats` retorna exactamente las 8 claves: `diabetes_dataset`, `dim_paciente`, `dim_ubicacion`, `dim_raza`, `dim_condicion`, `fact_diabetes`, `total_con_diabetes`, `total_sin_diabetes` (Requisito 3.1).
- [ ] 3.2 Verificar que `total_con_diabetes` es `int(df["diabetes"].sum())` y `total_sin_diabetes` es `int((df["diabetes"] == 0).sum())` (Requisito 3.2).
- [ ] 3.3 Verificar que cada Tabla_Virtual se genera invocando su función correspondiente del TABLAS_MAP y se retorna su `len()` (Requisito 3.2).

**Archivos afectados:** `backend/app/main.py`
**Valida:** Requisito 3.1, 3.2, Property 6

---

## Tarea 4: Backend — Endpoint `GET /api/tabla/{nombre}` con TABLAS_MAP

- [ ] 4.1 Verificar que el parámetro `limit` usa `Query(default=50, ge=1, le=500)` para que FastAPI retorne HTTP 422 automáticamente para valores fuera de rango (Requisito 2.6).
- [ ] 4.2 Verificar que la validación contra el TABLAS_MAP ocurre antes de invocar `get_df()` (Requisito 9.1, 9.2).
- [ ] 4.3 Verificar que cuando el nombre no está en el TABLAS_MAP, se retorna HTTP 400 con `detail` que lista las opciones válidas (Requisito 2.4).
- [ ] 4.4 Verificar que la respuesta contiene `total` (número total de filas de la Tabla_Virtual) y `rows` (lista de dicts con las primeras `limit` filas) (Requisito 2.2, 2.3).
- [ ] 4.5 Verificar que si MinIO falla al cargar el Dataset, el error HTTP se propaga correctamente (Requisito 2.7).

**Archivos afectados:** `backend/app/main.py`
**Valida:** Requisito 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 9.1, 9.2, Property 1, Property 2, Property 3

---

## Tarea 5: Backend — CRUD `GET/PUT/DELETE /api/fact/{id_fact}`

- [ ] 5.1 Verificar que `GET /api/fact/{id_fact}` retorna el registro completo del Dataset en la posición `id_fact` como dict JSON (Requisito 5.1).
- [ ] 5.2 Verificar que `GET /api/fact/{id_fact}` retorna HTTP 404 con `"Registro no encontrado"` para `id_fact < 0` o `id_fact >= len(df)` (Requisito 5.2).
- [ ] 5.3 Verificar que `PUT /api/fact/{id_fact}` actualiza solo los campos provistos (no nulos) en `_df_cache` usando `_df_cache.at[id_fact, campo] = valor` (Requisito 5.3).
- [ ] 5.4 Verificar que `PUT /api/fact/{id_fact}` retorna HTTP 200 con `ok: true` y el registro actualizado completo (Requisito 5.4).
- [ ] 5.5 Verificar que `DELETE /api/fact/{id_fact}` elimina la fila y reindexea el DataFrame con `reset_index(drop=True)` (Requisito 5.5).
- [ ] 5.6 Verificar que `DELETE /api/fact/{id_fact}` retorna HTTP 200 con `ok: true` y `registros_restantes` igual a `len(_df_cache)` tras la eliminación (Requisito 5.6).
- [ ] 5.7 Verificar que `PUT` y `DELETE` retornan HTTP 404 para `id_fact` fuera de rango (Requisito 5.7).

**Archivos afectados:** `backend/app/main.py`
**Valida:** Requisito 5.1–5.7, Property 10, Property 11

---

## Tarea 6: Backend — Endpoints de charts

- [ ] 6.1 Verificar que `/api/chart/diabetes-por-anio` agrupa por `year`, cuenta registros con `diabetes == 1` y `diabetes == 0`, y retorna la lista ordenada ascendentemente por `anio` (Requisito 4.1, 4.2).
- [ ] 6.2 Verificar que `/api/chart/pacientes-por-ubicacion` agrupa por `location`, ordena descendentemente por `total` y limita a 15 resultados (Requisito 4.3, 4.4).
- [ ] 6.3 Verificar que `/api/chart/distribucion-bmi` usa `pd.cut` con los 6 rangos definidos y retorna exactamente 6 categorías (Requisito 4.5).
- [ ] 6.4 Verificar que `/api/chart/glucosa-vs-diabetes` agrupa por `diabetes`, calcula el promedio de `blood_glucose_level` y mapea los valores 0/1 a `"Sin diabetes"`/`"Con diabetes"` (Requisito 4.6).
- [ ] 6.5 Verificar que todos los endpoints de chart retornan `[]` con HTTP 200 cuando el Dataset está vacío (Requisito 4.7).

**Archivos afectados:** `backend/app/main.py`
**Valida:** Requisito 4.1–4.7, Property 8, Property 9

---

## Tarea 7: Backend — Endpoint `GET /api/empresa`

- [ ] 7.1 Verificar que la respuesta contiene exactamente los 7 campos: `nombre`, `slogan`, `mision`, `vision`, `objetivos_estrategicos`, `objetivos_tacticos`, `objetivos_operacionales` (Requisito 6.1).
- [ ] 7.2 Verificar que `objetivos_estrategicos`, `objetivos_tacticos` y `objetivos_operacionales` tienen exactamente 3 elementos cada uno (Requisito 6.2).

**Archivos afectados:** `backend/app/main.py`
**Valida:** Requisito 6.1, 6.2, Property 7

---

## Tarea 8: Frontend — Dashboard: carga automática de stats y tarjeta de error

- [ ] 8.1 Verificar que `loadStats()` se invoca automáticamente al cargar la página y al navegar a la sección Dashboard (Requisito 3.3).
- [ ] 8.2 Verificar que cada tarjeta muestra la etiqueta legible del objeto `STAT_META` y el conteo formateado con `toLocaleString()` (Requisito 3.3).
- [ ] 8.3 Verificar que cuando `fetch('/api/stats')` falla con error de red o respuesta no-2xx, se muestra una tarjeta de error indicando ausencia de conexión (Requisito 3.4, 11.2).
- [ ] 8.4 Verificar que el grid muestra las 8 tarjetas cuando la respuesta es exitosa, incluyendo `total_con_diabetes` con color verde y `total_sin_diabetes` con color verde.

**Archivos afectados:** `frontend/templates/index.html`
**Valida:** Requisito 3.3, 3.4, 11.2

---

## Tarea 9: Frontend — Ver Tablas: renderizado, info y estado vacío

- [ ] 9.1 Verificar que el selector de tablas incluye exactamente las 6 opciones del TABLAS_MAP: `diabetes_dataset`, `dim_paciente`, `dim_ubicacion`, `dim_raza`, `dim_condicion`, `fact_diabetes` (Requisito 2.5).
- [ ] 9.2 Verificar que cuando `rows` tiene al menos una fila, se renderiza una tabla HTML con `<th>` por cada columna y `<td>` por cada valor (Requisito 2.8).
- [ ] 9.3 Verificar que el texto de `table-info` muestra "N de M registros · K columnas" con los valores correctos de `rows.length`, `data.total` y `cols.length` (Requisito 2.9).
- [ ] 9.4 Verificar que cuando `total === 0` o `rows` está vacío, se muestra el estado vacío en lugar de la tabla HTML (Requisito 2.10).
- [ ] 9.5 Verificar que cuando `fetch` falla por error de red, se muestra el mensaje de error en `#table-wrapper` reemplazando el contenido previo (Requisito 11.3).

**Archivos afectados:** `frontend/templates/index.html`
**Valida:** Requisito 2.5, 2.8, 2.9, 2.10, 11.3

---

## Tarea 10: Frontend — CRUD Fact: formularios, alertas y flujo completo

- [ ] 10.1 Verificar que el formulario de lectura invoca `GET /api/fact/{id}` y muestra los campos `bmi`, `hbA1c_level`, `blood_glucose_level` y `diabetes` en la alerta verde (Requisito 5.1, 5.8).
- [ ] 10.2 Verificar que el formulario de actualización construye los query params solo con los campos no vacíos y envía `PUT /api/fact/{id}?...` (Requisito 5.3).
- [ ] 10.3 Verificar que el formulario de eliminación muestra un `confirm()` antes de enviar `DELETE /api/fact/{id}` (Requisito 5.5).
- [ ] 10.4 Verificar que `showAlert(id, msg, ok)` muestra la alerta con clase `ok` (verde) o `err` (rojo) y la oculta automáticamente tras 5 segundos (Requisito 5.8, 5.9).
- [ ] 10.5 Verificar que cuando el backend retorna un error HTTP, la alerta muestra `data.detail` con estilo rojo (Requisito 5.9, 11.4).

**Archivos afectados:** `frontend/templates/index.html`
**Valida:** Requisito 5.1–5.9, 11.4

---

## Tarea 11: Frontend — Pipeline: visualización de arquitectura y recarga

- [ ] 11.1 Verificar que la sección Pipeline muestra los 5 componentes del flujo: PocketBase → Airflow DAG → Parquet → MinIO Stage → FastAPI, con sus identificadores (Requisito 7.1).
- [ ] 11.2 Verificar que cada componente tiene una tarjeta con descripción de su rol en el pipeline (Requisito 7.2).
- [ ] 11.3 Verificar que el botón "Recargar Dataset" invoca `POST /api/cargar-dataset`, muestra spinner durante la operación y muestra el resultado en la alerta (Requisito 7.3, 1.9, 1.10).
- [ ] 11.4 Verificar que el botón se deshabilita durante la recarga y se rehabilita al finalizar (Requisito 1.9, 1.10).

**Archivos afectados:** `frontend/templates/index.html`
**Valida:** Requisito 1.9, 1.10, 7.1, 7.2, 7.3

---

## Tarea 12: Frontend — Empresa y Objetivos: caché y renderizado

- [ ] 12.1 Verificar que `empresaData` se reutiliza sin nueva petición HTTP al navegar entre las secciones Empresa y Objetivos (Requisito 6.5).
- [ ] 12.2 Verificar que la sección Empresa muestra `mision` y `vision` en tarjetas separadas con encabezados identificadores (Requisito 6.3).
- [ ] 12.3 Verificar que la sección Objetivos muestra los tres arrays en secciones con encabezados "Estratégicos", "Tácticos" y "Operacionales" (Requisito 6.4).
- [ ] 12.4 Verificar que el responsive CSS reorganiza las grillas de dos columnas en una sola columna cuando el ancho es inferior a 1200px, y reduce el sidebar a 200px bajo 900px (Requisito 10.5).

**Archivos afectados:** `frontend/templates/index.html`
**Valida:** Requisito 6.3, 6.4, 6.5, 10.5

---

## Tarea 13: Tests — PBT Properties 1 y 2: TABLAS_MAP rechaza/acepta tablas

- [ ] 13.1 Crear el archivo `tests/test_tablas_map_pbt.py` con la configuración de Hypothesis (`settings(max_examples=100)`).
- [ ] 13.2 Implementar la prueba PBT para **Property 1**: dado cualquier string que no pertenezca al TABLAS_MAP, `GET /api/tabla/{nombre}` retorna HTTP 400. Usar `st.text().filter(lambda s: s not in TABLAS_MAP)`.
- [ ] 13.3 Implementar la prueba PBT para **Property 2**: dado cualquier nombre del TABLAS_MAP, `GET /api/tabla/{nombre}` retorna HTTP 200 con `rows` y `total`. Usar `st.sampled_from(list(TABLAS_MAP.keys()))` con DataFrame mockeado en `_df_cache`.
- [ ] 13.4 Agregar los tags `# Feature: diabcare-analytics, Property 1` y `# Feature: diabcare-analytics, Property 2`.
- [ ] 13.5 Ejecutar los tests y confirmar que pasan.

**Archivos afectados:** `tests/test_tablas_map_pbt.py`
**Valida:** Requisito 2.4, 2.5, 9.1, 9.2, Property 1, Property 2

---

## Tarea 14: Tests — PBT Property 3: Contrato del parámetro `limit`

- [ ] 14.1 Crear el archivo `tests/test_limit_pbt.py`.
- [ ] 14.2 Implementar la prueba PBT para **Property 3 (rango válido)**: dado cualquier tabla del TABLAS_MAP y cualquier `limit` en [1, 500], `len(rows) <= limit` y `total >= len(rows)`. Usar `st.integers(min_value=1, max_value=500)` con DataFrame mockeado.
- [ ] 14.3 Implementar la prueba PBT para **Property 3 (rango inválido)**: dado cualquier `limit` fuera de [1, 500], el endpoint retorna HTTP 422. Usar `st.integers().filter(lambda x: x < 1 or x > 500)`.
- [ ] 14.4 Agregar el tag `# Feature: diabcare-analytics, Property 3: contrato del parámetro limit`.
- [ ] 14.5 Ejecutar los tests y confirmar que pasan.

**Archivos afectados:** `tests/test_limit_pbt.py`
**Valida:** Requisito 2.1, 2.2, 2.6, Property 3

---

## Tarea 15: Tests — PBT Properties 4 y 5: caché y tablas virtuales deterministas

- [ ] 15.1 Crear el archivo `tests/test_cache_pbt.py`.
- [ ] 15.2 Implementar la prueba PBT para **Property 4**: mockear MinIO para que `get_df()` retorne un DataFrame fijo. Invocar `get_df()` dos veces y verificar que la segunda invocación no llama a MinIO (usando `unittest.mock.patch`). Usar `settings(max_examples=20)`.
- [ ] 15.3 Implementar la prueba PBT para **Property 5**: dado un DataFrame generado aleatoriamente con `n_rows` filas, invocar cada función de dimensión dos veces y verificar que el número de filas y las columnas son iguales en ambas invocaciones. Usar `st.integers(min_value=10, max_value=500)`.
- [ ] 15.4 Agregar los tags `# Feature: diabcare-analytics, Property 4` y `# Feature: diabcare-analytics, Property 5`.
- [ ] 15.5 Ejecutar los tests y confirmar que pasan.

**Archivos afectados:** `tests/test_cache_pbt.py`
**Valida:** Requisito 1.3, 8.2, Property 4, Property 5

---

## Tarea 16: Tests — PBT Property 6: Stats siempre retorna 8 claves con valores ≥ 0

- [ ] 16.1 Crear el archivo `tests/test_stats_pbt.py`.
- [ ] 16.2 Implementar la prueba PBT para **Property 6**: mockear `_df_cache` con DataFrames de distintos tamaños (incluyendo 0 filas). Verificar que la respuesta siempre tiene exactamente 8 claves y todos los valores son enteros ≥ 0. Usar `st.integers(min_value=0, max_value=1000)`.
- [ ] 16.3 Agregar el tag `# Feature: diabcare-analytics, Property 6: stats siempre retorna las 8 claves con valores no negativos`.
- [ ] 16.4 Ejecutar los tests y confirmar que pasan.

**Archivos afectados:** `tests/test_stats_pbt.py`
**Valida:** Requisito 3.1, 3.2, Property 6

---

## Tarea 17: Tests — PBT Property 7: Empresa tiene estructura y cardinalidad fijas

- [ ] 17.1 Crear el archivo `tests/test_empresa_pbt.py`.
- [ ] 17.2 Implementar la prueba PBT para **Property 7**: invocar `GET /api/empresa` y verificar que la respuesta contiene exactamente los 7 campos y que los tres arrays de objetivos tienen longitud 3. Usar `settings(max_examples=1)`.
- [ ] 17.3 Agregar el tag `# Feature: diabcare-analytics, Property 7: respuesta de empresa tiene estructura y cardinalidad fijas`.
- [ ] 17.4 Ejecutar los tests y confirmar que pasan.

**Archivos afectados:** `tests/test_empresa_pbt.py`
**Valida:** Requisito 6.1, 6.2, Property 7

---

## Tarea 18: Tests — PBT Properties 8 y 9: Estructura y ordenamiento de charts

- [ ] 18.1 Crear el archivo `tests/test_charts_pbt.py`.
- [ ] 18.2 Implementar la prueba PBT para **Property 8**: mockear `_df_cache` con DataFrames aleatorios. Verificar que cada elemento de los 4 endpoints de chart tiene los campos correctos y que `pacientes-por-ubicacion` tiene ≤ 15 elementos y `glucosa-vs-diabetes` tiene exactamente 2 elementos. Usar `st.integers(min_value=2, max_value=200)` para el tamaño del DF.
- [ ] 18.3 Implementar la prueba PBT para **Property 9**: mockear `_df_cache` con al menos 2 años y 2 ubicaciones distintas. Verificar el ordenamiento ascendente de `diabetes-por-anio` y descendente de `pacientes-por-ubicacion`. Usar `st.integers(min_value=2, max_value=10)` para el número de grupos.
- [ ] 18.4 Agregar los tags `# Feature: diabcare-analytics, Property 8` y `# Feature: diabcare-analytics, Property 9`.
- [ ] 18.5 Ejecutar los tests y confirmar que pasan.

**Archivos afectados:** `tests/test_charts_pbt.py`
**Valida:** Requisito 4.1–4.7, Property 8, Property 9

---

## Tarea 19: Tests — PBT Properties 10 y 11: CRUD límites e integridad de DELETE

- [ ] 19.1 Agregar al archivo `tests/test_crud_pbt.py` la prueba PBT para **Property 10**: dado un DataFrame de N filas mockeado en `_df_cache`, verificar que `GET`, `PUT` y `DELETE /api/fact/{id_fact}` retornan HTTP 404 para cualquier `id_fact < 0` o `id_fact >= N`. Usar `st.integers(min_value=1, max_value=100)` para N y `st.integers().filter(lambda x: x < 0 or x >= N)` para el id.
- [ ] 19.2 Implementar la prueba PBT para **Property 11**: dado un DataFrame de N filas y un `id_fact` válido, tras `DELETE /api/fact/{id_fact}` verificar que `len(_df_cache) == N - 1` y que los índices son contiguos desde 0. Usar `st.integers(min_value=1, max_value=100)` para N.
- [ ] 19.3 Agregar los tags `# Feature: diabcare-analytics, Property 10` y `# Feature: diabcare-analytics, Property 11`.
- [ ] 19.4 Ejecutar los tests y confirmar que pasan.

**Archivos afectados:** `tests/test_crud_pbt.py`
**Valida:** Requisito 5.2, 5.5, 5.6, 5.7, Property 10, Property 11

---

## Tarea 20: Tests — Integración, unitarios y smoke tests

- [ ] 20.1 Crear `tests/test_unit.py` con tests unitarios para:
  - Cada una de las 6 tablas del TABLAS_MAP pasa la validación (HTTP 200 con DF mockeado).
  - Nombres arbitrarios (`""`, `"pg_tables"`, `"'; DROP TABLE --"`) son rechazados con HTTP 400.
  - `get_dim_paciente`, `get_dim_ubicacion`, `get_dim_raza`, `get_dim_condicion`, `get_fact_diabetes` retornan DataFrames con las columnas correctas dado un DF de prueba.
  - MinIO sin objetos → HTTP 404 con `"No hay archivos parquet en MinIO stage/"`.
  - MinIO sin `.parquet` → HTTP 404 con `"No se encontraron archivos .parquet"`.
  - `/api/empresa` retorna arrays con longitudes 3, 3, 3.
  - `PUT /api/fact/0` con `bmi=99.9` actualiza el valor en `_df_cache`.
  - `DELETE /api/fact/0` reduce el conteo en 1 y reindexea.
- [ ] 20.2 Crear `tests/test_smoke.py` con smoke tests que:
  - Verifican que `GET /` retorna HTTP 200 con contenido HTML (usando `TestClient` de FastAPI).
  - Verifican que `GET /api/stats` retorna HTTP 200 con exactamente 8 claves (con DF mockeado).
  - Verifican que `GET /api/empresa` retorna HTTP 200 con los 7 campos requeridos.
- [ ] 20.3 Crear `tests/conftest.py` con el fixture `client` de `TestClient(app)` y fixtures de mock de MinIO y `_df_cache` reutilizables.
- [ ] 20.4 Crear `tests/__init__.py` vacío para que pytest descubra los tests.
- [ ] 20.5 Ejecutar `pytest tests/ -v` y confirmar que todos los tests pasan.

**Archivos afectados:** `tests/test_unit.py`, `tests/test_smoke.py`, `tests/conftest.py`, `tests/__init__.py`
**Valida:** Todos los requisitos funcionales y no funcionales

---

## Resumen de Archivos por Tarea

| Tarea | Archivo principal | Tipo |
|---|---|---|
| 1 | `backend/app/main.py` | Backend — MinIO/caché |
| 2 | `backend/app/main.py` | Backend — recarga |
| 3 | `backend/app/main.py` | Backend — stats |
| 4 | `backend/app/main.py` | Backend — tablas |
| 5 | `backend/app/main.py` | Backend — CRUD |
| 6 | `backend/app/main.py` | Backend — charts |
| 7 | `backend/app/main.py` | Backend — empresa |
| 8 | `frontend/templates/index.html` | Frontend — Dashboard |
| 9 | `frontend/templates/index.html` | Frontend — Tablas |
| 10 | `frontend/templates/index.html` | Frontend — CRUD |
| 11 | `frontend/templates/index.html` | Frontend — Pipeline |
| 12 | `frontend/templates/index.html` | Frontend — Empresa |
| 13 | `tests/test_tablas_map_pbt.py` | PBT |
| 14 | `tests/test_limit_pbt.py` | PBT |
| 15 | `tests/test_cache_pbt.py` | PBT |
| 16 | `tests/test_stats_pbt.py` | PBT |
| 17 | `tests/test_empresa_pbt.py` | PBT |
| 18 | `tests/test_charts_pbt.py` | PBT |
| 19 | `tests/test_crud_pbt.py` | PBT |
| 20 | `tests/test_unit.py`, `tests/test_smoke.py` | Integración |
