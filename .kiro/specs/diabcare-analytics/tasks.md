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

- [ ] 1.1 Definir constantes de conexión MinIO en `configuracion/Ajustes.py` (`MINIO_ENDPOINT`, `MINIO_ACCESS`, `MINIO_SECRET`, `MINIO_BUCKET`, `MINIO_PREFIX`).
- [ ] 1.2 Implementar `get_minio_client()` en `backend/base_de_datos/ClienteMinio.py` con `secure=False`.
- [ ] 1.3 Implementar `get_df()` en `backend/servicios/ServicioDataset.py`: lista objetos en `stage/`, filtra `.parquet`, selecciona el más reciente por `last_modified`, carga con `pd.read_parquet(BytesIO(...))`.
- [ ] 1.4 Verificar que `get_df()` almacena el DataFrame en `_df_cache` y retorna la caché en llamadas posteriores sin volver a conectarse a MinIO.
- [ ] 1.5 Verificar que `get_df()` lanza `HTTPException(404)` cuando no hay objetos en `stage/`.
- [ ] 1.6 Verificar que `get_df()` lanza `HTTPException(404)` cuando no hay archivos `.parquet`.

**Archivos afectados:** `backend/Principal.py`, `backend/base_de_datos/ClienteMinio.py`, `backend/servicios/ServicioDataset.py`, `configuracion/Ajustes.py`
**Valida:** Requisito 1.2, 1.3, 1.6, 1.7, 1.8

---

## Tarea 2: Backend — Endpoint `POST /api/cargar-dataset`

- [ ] 2.1 Implementar en `backend/api/RutasDataset.py`: asignar `_df_cache = None` antes de invocar `get_df()`.
- [ ] 2.2 Verificar que la respuesta exitosa contiene `ok: true`, `registros` y `columnas`.
- [ ] 2.3 Verificar que si MinIO no está disponible, propaga HTTP 500.

**Archivos afectados:** `backend/api/RutasDataset.py`, `backend/servicios/ServicioDataset.py`
**Valida:** Requisito 1.4, 1.5, 1.8

---

## Tarea 3: Backend — Endpoint `GET /api/stats`

- [ ] 3.1 Implementar en `backend/api/RutasDataset.py`: retornar exactamente las 8 claves.
- [ ] 3.2 Calcular `total_con_diabetes` con `int(df["diabetes"].sum())` y `total_sin_diabetes` con `int((df["diabetes"] == 0).sum())`.
- [ ] 3.3 Generar cada Tabla_Virtual desde `backend/servicios/ServicioCrud.py` y retornar su `len()`.

**Archivos afectados:** `backend/api/RutasDataset.py`, `backend/servicios/ServicioCrud.py`
**Valida:** Requisito 3.1, 3.2

---

## Tarea 4: Backend — Endpoint `GET /api/tabla/{nombre}` con TABLAS_MAP

- [ ] 4.1 Implementar parámetro `limit` con `Query(default=50, ge=1, le=500)` en `backend/api/RutasDataset.py`.
- [ ] 4.2 Validar nombre contra TABLAS_MAP antes de invocar `get_df()`.
- [ ] 4.3 Retornar HTTP 400 con opciones válidas si el nombre no está en TABLAS_MAP.
- [ ] 4.4 Retornar `total` y `rows` con las primeras `limit` filas.

**Archivos afectados:** `backend/api/RutasDataset.py`, `backend/servicios/ServicioCrud.py`
**Valida:** Requisito 2.1–2.7, 9.1, 9.2

---

## Tarea 5: Backend — CRUD `GET/PUT/DELETE /api/fact/{id_fact}`

- [ ] 5.1 Implementar `GET /api/fact/{id_fact}` en `backend/api/RutasCrud.py`.
- [ ] 5.2 Retornar HTTP 404 con `"Registro no encontrado"` para `id_fact` fuera de rango.
- [ ] 5.3 Implementar `PUT /api/fact/{id_fact}` actualizando solo campos provistos con `_df_cache.at[id_fact, campo] = valor`.
- [ ] 5.4 Retornar HTTP 200 con `ok: true` y registro actualizado.
- [ ] 5.5 Implementar `DELETE /api/fact/{id_fact}` eliminando fila y reindexando con `reset_index(drop=True)`.
- [ ] 5.6 Retornar HTTP 200 con `ok: true` y `registros_restantes`.

**Archivos afectados:** `backend/api/RutasCrud.py`, `backend/servicios/ServicioCrud.py`
**Valida:** Requisito 5.1–5.7

---

## Tarea 6: Backend — Endpoints de charts

- [ ] 6.1 Implementar los 4 endpoints de chart en `backend/api/RutasDataset.py`.
- [ ] 6.2 `diabetes-por-anio`: agrupar por `year`, ordenar ascendente.
- [ ] 6.3 `pacientes-por-ubicacion`: agrupar por `location`, ordenar descendente, limitar a 15.
- [ ] 6.4 `distribucion-bmi`: usar `pd.cut` con 6 rangos.
- [ ] 6.5 `glucosa-vs-diabetes`: promedio de `blood_glucose_level` por grupo `diabetes`.

**Archivos afectados:** `backend/api/RutasDataset.py`
**Valida:** Requisito 4.1–4.7

---

## Tarea 7: Backend — Endpoint `GET /api/empresa`

- [ ] 7.1 Implementar en `backend/api/RutasDataset.py` retornando los 7 campos.
- [ ] 7.2 Verificar que cada array de objetivos tiene exactamente 3 elementos.

**Archivos afectados:** `backend/api/RutasDataset.py`
**Valida:** Requisito 6.1, 6.2

---

## Tarea 8: Frontend — Dashboard

- [ ] 8.1 Implementar `loadStats()` en `frontend/paginas/Inicio.html` que se invoca al cargar la página.
- [ ] 8.2 Renderizar tarjetas con conteos formateados con `toLocaleString()`.
- [ ] 8.3 Mostrar tarjeta de error si `/api/stats` falla.

**Archivos afectados:** `frontend/paginas/Inicio.html`, `frontend/estaticos/scripts/Estadisticas.js`
**Valida:** Requisito 3.3, 3.4

---

## Tarea 9: Frontend — Ver Tablas

- [ ] 9.1 Selector con las 6 tablas del TABLAS_MAP.
- [ ] 9.2 Renderizar tabla HTML con `<th>` y `<td>`.
- [ ] 9.3 Mostrar "N de M registros · K columnas".
- [ ] 9.4 Mostrar estado vacío cuando `total === 0`.

**Archivos afectados:** `frontend/paginas/Inicio.html`, `frontend/estaticos/scripts/Api.js`
**Valida:** Requisito 2.5, 2.8–2.10

---

## Tarea 10: Frontend — CRUD Fact

- [ ] 10.1 Formulario de lectura: `GET /api/fact/{id}`.
- [ ] 10.2 Formulario de actualización: `PUT /api/fact/{id}` solo con campos no vacíos.
- [ ] 10.3 Formulario de eliminación: `confirm()` antes de `DELETE /api/fact/{id}`.
- [ ] 10.4 `showAlert()`: alerta verde/roja que se oculta automáticamente tras 5 segundos.

**Archivos afectados:** `frontend/paginas/Inicio.html`, `frontend/estaticos/scripts/Crud.js`
**Valida:** Requisito 5.1–5.9

---

## Tarea 11: Frontend — Pipeline + Recarga

- [ ] 11.1 Mostrar los 5 componentes del flujo con descripción de cada uno.
- [ ] 11.2 Botón "Recargar Dataset" con spinner durante operación.
- [ ] 11.3 Deshabilitar botón durante recarga y rehabilitar al finalizar.

**Archivos afectados:** `frontend/paginas/Inicio.html`
**Valida:** Requisito 1.9, 1.10, 7.1, 7.2

---

## Tarea 12: Frontend — Empresa y Objetivos

- [ ] 12.1 Reutilizar `empresaData` sin nueva petición al navegar entre secciones.
- [ ] 12.2 Mostrar `mision` y `vision` en tarjetas separadas.
- [ ] 12.3 Mostrar objetivos en secciones con encabezados "Estratégicos", "Tácticos" y "Operacionales".

**Archivos afectados:** `frontend/paginas/Inicio.html`
**Valida:** Requisito 6.3, 6.4, 6.5

---

## Tarea 13: Pruebas — PBT Properties 1 y 2: TABLAS_MAP

- [ ] 13.1 Crear `pruebas/api/PruebaTablasMapa.py` con Hypothesis (`settings(max_examples=100)`).
- [ ] 13.2 Property 1: cualquier string fuera del TABLAS_MAP → HTTP 400.
- [ ] 13.3 Property 2: cualquier nombre del TABLAS_MAP → HTTP 200 con `rows` y `total`.
- [ ] 13.4 Ejecutar y confirmar que pasan.

**Archivos afectados:** `pruebas/api/PruebaTablasMapa.py`
**Valida:** Requisito 2.4, 2.5, 9.1, 9.2

---

## Tarea 14: Pruebas — PBT Property 3: Parámetro `limit`

- [ ] 14.1 Crear `pruebas/api/PruebaLimit.py`.
- [ ] 14.2 Property 3 (válido): `limit` en [1, 500] → `len(rows) <= limit` y `total >= len(rows)`.
- [ ] 14.3 Property 3 (inválido): `limit` fuera de [1, 500] → HTTP 422.
- [ ] 14.4 Ejecutar y confirmar que pasan.

**Archivos afectados:** `pruebas/api/PruebaLimit.py`
**Valida:** Requisito 2.1, 2.2, 2.6

---

## Tarea 15: Pruebas — PBT Properties 4 y 5: Caché y Tablas Virtuales

- [ ] 15.1 Crear `pruebas/api/PruebaCache.py`.
- [ ] 15.2 Property 4: invocar `get_df()` dos veces → segunda invocación no llama a MinIO.
- [ ] 15.3 Property 5: dado un DataFrame aleatorio → cada función de dimensión retorna mismas columnas en ambas invocaciones.

**Archivos afectados:** `pruebas/api/PruebaCache.py`
**Valida:** Requisito 1.3, 8.2

---

## Tarea 16: Pruebas — PBT Property 6: Stats

- [ ] 16.1 Crear `pruebas/api/PruebaStats.py`.
- [ ] 16.2 Property 6: respuesta siempre tiene 8 claves con valores enteros ≥ 0.

**Archivos afectados:** `pruebas/api/PruebaStats.py`
**Valida:** Requisito 3.1, 3.2

---

## Tarea 17: Pruebas — PBT Property 7: Empresa

- [ ] 17.1 Crear `pruebas/api/PruebaEmpresa.py`.
- [ ] 17.2 Property 7: respuesta tiene 7 campos y arrays de objetivos con longitud 3.

**Archivos afectados:** `pruebas/api/PruebaEmpresa.py`
**Valida:** Requisito 6.1, 6.2

---

## Tarea 18: Pruebas — PBT Properties 8 y 9: Charts

- [ ] 18.1 Crear `pruebas/api/PruebaGraficas.py`.
- [ ] 18.2 Property 8: campos correctos en cada endpoint de chart, `pacientes-por-ubicacion` ≤ 15 elementos.
- [ ] 18.3 Property 9: `diabetes-por-anio` ordenado ascendente, `pacientes-por-ubicacion` descendente.

**Archivos afectados:** `pruebas/api/PruebaGraficas.py`
**Valida:** Requisito 4.1–4.7

---

## Tarea 19: Pruebas — PBT Properties 10 y 11: CRUD

- [ ] 19.1 Crear `pruebas/api/PruebaCrud.py`.
- [ ] 19.2 Property 10: `id_fact` fuera de rango → HTTP 404 en GET, PUT y DELETE.
- [ ] 19.3 Property 11: tras DELETE válido → `len(_df_cache) == N - 1` e índices contiguos desde 0.

**Archivos afectados:** `pruebas/api/PruebaCrud.py`
**Valida:** Requisito 5.2, 5.5, 5.6, 5.7

---

## Tarea 20: Pruebas — Integración y Smoke Tests

- [ ] 20.1 Crear `pruebas/integracion/PruebaIntegracion.py` con:
  - Descarga real del parquet desde MinIO local.
  - Las 5 Tablas_Virtuales se generan sin errores.
  - `POST /api/cargar-dataset` invalida caché y retorna conteo correcto.
  - `PUT /api/fact/0` con `bmi=99.9` actualiza el valor.
  - `DELETE /api/fact/0` reduce el conteo en 1 y reindexea.
- [ ] 20.2 Crear `pruebas/integracion/PruebaHumo.py` con:
  - `GET /` retorna HTTP 200 con contenido HTML.
  - `GET /api/stats` retorna HTTP 200 con 8 claves.
  - `GET /api/empresa` retorna HTTP 200 con 7 campos.
- [ ] 20.3 Ejecutar `pytest pruebas/ -v` y confirmar que todos pasan.

**Archivos afectados:** `pruebas/integracion/PruebaIntegracion.py`, `pruebas/integracion/PruebaHumo.py`
**Valida:** Todos los requisitos funcionales y no funcionales

---

## Resumen de Archivos por Tarea

| Tarea | Archivo principal | Tipo |
|---|---|---|
| 1 | `backend/servicios/ServicioDataset.py` | Backend — MinIO/caché |
| 2 | `backend/api/RutasDataset.py` | Backend — recarga |
| 3 | `backend/api/RutasDataset.py` | Backend — stats |
| 4 | `backend/api/RutasDataset.py` | Backend — tablas |
| 5 | `backend/api/RutasCrud.py` | Backend — CRUD |
| 6 | `backend/api/RutasDataset.py` | Backend — charts |
| 7 | `backend/api/RutasDataset.py` | Backend — empresa |
| 8 | `frontend/paginas/Inicio.html` | Frontend — Dashboard |
| 9 | `frontend/paginas/Inicio.html` | Frontend — Tablas |
| 10 | `frontend/paginas/Inicio.html` | Frontend — CRUD |
| 11 | `frontend/paginas/Inicio.html` | Frontend — Pipeline |
| 12 | `frontend/paginas/Inicio.html` | Frontend — Empresa |
| 13 | `pruebas/api/PruebaTablasMapa.py` | PBT |
| 14 | `pruebas/api/PruebaLimit.py` | PBT |
| 15 | `pruebas/api/PruebaCache.py` | PBT |
| 16 | `pruebas/api/PruebaStats.py` | PBT |
| 17 | `pruebas/api/PruebaEmpresa.py` | PBT |
| 18 | `pruebas/api/PruebaGraficas.py` | PBT |
| 19 | `pruebas/api/PruebaCrud.py` | PBT |
| 20 | `pruebas/integracion/PruebaIntegracion.py` | Integración |
