# Implementation Plan

## Overview

Este plan cubre DiabCare Analytics v2.0 y la ampliación **DiabCare Hospital** (P16–P20, comorbilidades, flujo E2E, calidad diabetes, mis citas/cobro). Documentación táctica TA11 (PostgreSQL BDR + MinIO columnar) vive en el entregable Word/PDF académico; estos MD reflejan trazabilidad en código.

Las tareas T1–T10 (núcleo analytics) y T16–T20 (hospital) están completadas en lo esencial. T11–T15 del núcleo histórico se actualizan abajo según implementación real (reportes fpdf2, auditoría Parquet, etc.).

## Tasks

### ✅ Tarea 1: Autenticación JWT

- [x] 1.1 Implementar `POST /api/auth/login` con validación SHA-256 y generación de JWT HS256 (8h).
- [x] 1.2 Implementar `verificar_token()` en `AutenticacionServicio.py` con validación de rol.
- [x] 1.3 Implementar `Dependencias.py` con `require_auth`, `require_admin`, `require_modulo()`.
- [x] 1.4 Definir `PERMISOS_MODULOS` con restricciones por rol para 12 módulos.
- [x] 1.5 Implementar usuario admin por defecto `admin@diabcare.com / Admin2026*` en startup.
- [x] 1.6 Implementar `POST /api/auth/recuperar` y `POST /api/auth/resetear` para reset de password.
- [x] 1.7 Implementar `PUT /api/auth/cambiar-password` con validación de password actual.
- [x] 1.8 Frontend login con validación de campos, spinner y redirección al Dashboard.

**Archivos:** `paquetes/autenticacion/AutenticacionRutas.py`, `paquetes/autenticacion/AutenticacionServicio.py`, `nucleo/utilidades/Dependencias.py`

---

### ✅ Tarea 2: Gestión de Usuarios

- [x] 2.1 Implementar `GET /api/usuarios/` retornando lista sin password_hash.
- [x] 2.2 Implementar `POST /api/usuarios/` con validación de email único y hash SHA-256.
- [x] 2.3 Implementar `PUT /api/usuarios/{id}/rol` para cambio de rol.
- [x] 2.4 Implementar `DELETE /api/usuarios/{id}` como desactivación (activo=False).
- [x] 2.5 Implementar `UsuariosServicio.py` con persistencia en `diabcare-app/usuarios/usuarios.parquet`.
- [x] 2.6 Frontend con KPI cards (total, activos, inactivos, admins).
- [x] 2.7 Frontend con búsqueda en tiempo real por nombre/email.
- [x] 2.8 Frontend con modal para crear usuario y cambiar rol.
- [x] 2.9 Frontend con avatares de inicial y colores por índice.
- [x] 2.10 Corrección de `rol: null` en usuario admin via script Python directo en MinIO.

**Archivos:** `paquetes/usuarios/UsuariosRutas.py`, `paquetes/usuarios/UsuariosServicio.py`, `frontend/paginas/seguridad/usuarios/index.html`

---

### ✅ Tarea 3: Registros Clínicos

- [x] 3.1 Implementar `_extraer()` que concatena todos los `.parquet` de `stage/` en un DataFrame unificado.
- [x] 3.2 Implementar `GET /api/registros/` con paginación skip/limit.
- [x] 3.3 Implementar `GET /api/registros/buscar` con filtros: diabetes, gender, location, age_min, age_max.
- [x] 3.4 Implementar `POST /api/registros/`, `PUT /api/registros/{id}`, `DELETE /api/registros/{id}`.
- [x] 3.5 Implementar `GET /api/registros/estadisticas` declarado ANTES de `/{encounter_id}` en el router.
- [x] 3.6 Estadísticas calculan: genero, tabaquismo, razas, edad (rangos pd.cut), promedios, comorbilidades, ubicaciones (top 10), tendencia por año.
- [x] 3.7 Frontend con tabla paginada y filtros por diabetes, género, ubicación y edad.

**Archivos:** `paquetes/registros_clinicos/RegistrosClinicosRutas.py`, `paquetes/registros_clinicos/RegistrosClinicosServicio.py`, `frontend/paginas/clinico/registros_clinicos/index.html`

---

### ✅ Tarea 4: Dataset y Generador Sintético

- [x] 4.1 Implementar `GET /api/dataset/hechos` con paginación y conteo rápido via pyarrow.
- [x] 4.2 Implementar `GET /api/dataset/dimension/{nombre}` para paciente, ubicacion, raza, condicion.
- [x] 4.3 Implementar `POST /api/dataset/generar` con parámetros `cantidad` y `year`.
- [x] 4.4 `generar_registro()` genera campos en español (género, tabaquismo, ubicaciones en español).
- [x] 4.5 Generador sube archivo Parquet a MinIO con nombre `sinteticos_{year}_{timestamp}.parquet`.
- [x] 4.6 Frontend generador con presets 1K/10K/50K/100K/500K.
- [x] 4.7 Frontend con barra de progreso animada y pasos: Generando → Parquet → MinIO → Completado.
- [x] 4.8 Frontend muestra card de resultado con registros, año, formato y nombre de archivo.
- [x] 4.9 Frontend ver tablas separado del generador en páginas independientes con 5 tabs.
- [x] 4.10 `GET /api/dataset/estadisticas` usa pyarrow para conteo rápido sin cargar todo en memoria.
- [x] 4.11 Frontend ver tablas muestra el total real concatenado de todos los parquets.

**Archivos:** `paquetes/dataset/DatasetRutas.py`, `paquetes/dataset/DatasetServicio.py`, `frontend/paginas/datos/dataset/index.html`, `frontend/paginas/datos/dataset/generador.html`

---

### ✅ Tarea 5: Estadísticas y Dashboard

- [x] 5.1 Dashboard consume `/api/registros/estadisticas` y `/api/dataset/estadisticas`.
- [x] 5.2 Dashboard muestra 4 KPI cards con barras de color inferiores.
- [x] 5.3 Dashboard muestra donut compacto con porcentajes calculados desde datos reales.
- [x] 5.4 Dashboard muestra 4 accesos rápidos con iconos.
- [x] 5.5 Dashboard genera alertas clínicas dinámicas: prevalencia > 50% → rojo, HbA1c > 7.5 → rojo, volumen < 1000 → azul.
- [x] 5.6 Dashboard muestra promedios clínicos con badges de color.
- [x] 5.7 Dashboard muestra top 6 ubicaciones con barras proporcionales.
- [x] 5.8 Dashboard muestra estado del sistema: MinIO, Dataset, API, Auth, Modelo ML, Pipeline.
- [x] 5.9 Dashboard muestra últimos archivos en MinIO con columnas del dataset.
- [x] 5.10 Página estadísticas con 10+ gráficas Chart.js: donut, género, comorbilidades, edad, raza, tabaquismo, ubicaciones, tendencia.
- [x] 5.11 KPI clínicos secundarios con BMI, HbA1c y glucosa promedio con/sin diabetes.
- [x] 5.12 Barras comparativas inline con animación CSS.

**Archivos:** `frontend/paginas/clinico/analisis/index.html`, `frontend/paginas/clinico/analisis/estadisticas/index.html`

---

### ✅ Tarea 6: Infraestructura y Sistema

- [x] 6.1 `Principal.py` sirve frontend multi-página con ruta dinámica `/paginas/{modulo}/{archivo}`.
- [x] 6.2 `inicializar_buckets()` crea buckets `diabetes-data` y `diabcare-app` en startup si no existen.
- [x] 6.3 `inicializar_admin()` crea usuario admin por defecto si Parquet de usuarios está vacío.
- [x] 6.4 `warnings.filterwarnings("ignore", category=UserWarning)` suprime logs de JWT key length.
- [x] 6.5 `GET /favicon.ico` retorna HTTP 204 para suprimir logs de 404.
- [x] 6.6 Uvicorn con `--no-access-log` para logs limpios en desarrollo.
- [x] 6.7 `estilos.css` como design system compartido con variables CSS y componentes reutilizables.
- [x] 6.8 Sidebar consistente en todas las páginas con `.user-row-wrap` + `.btn-logout` (icono ⏻).

**Archivos:** `Principal.py`, `paquetes/configuracion/ConfiguracionClienteMinio.py`, `frontend/estaticos/estilos.css`

---

### ✅ Tarea 7: Predicción ML

- [x] 7.1 Instalar scikit-learn: `pip install scikit-learn --break-system-packages`.
- [x] 7.2 Implementar `PrediccionServicio.py` con `entrenar()`, `predecir()`, `obtener_metricas()`, `modelo_disponible()`.
- [x] 7.3 `entrenar()` carga DataFrame completo via `_extraer()`, entrena `RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)` con split 80/20 estratificado.
- [x] 7.4 Modelo serializado con pickle junto a métricas en MinIO `diabcare-app/modelos/modelo_diabetes.pkl`.
- [x] 7.5 `_modelo_cache = {"modelo": None, "metricas": None}` para caché en memoria.
- [x] 7.6 Features: `["age", "bmi", "hbA1c_level", "blood_glucose_level", "hypertension", "heart_disease"]`.
- [x] 7.7 Nivel de riesgo: probabilidad >= 0.7 → Alto, >= 0.4 → Medio, < 0.4 → Bajo.
- [x] 7.8 Implementar `PrediccionRutas.py` con `POST /entrenar`, `POST /`, `GET /metricas`, `GET /estado`.
- [x] 7.9 Frontend `prediccion/index.html` con 4 metric cards, formulario 6 campos y resultado visual.
- [x] 7.10 Resultado muestra diagnóstico, barra de probabilidad animada y badge de riesgo.
- [x] 7.11 Llamar `aplicarRoles()` dentro de la función `predecir()` para evitar flash del sidebar.
- [x] 7.12 Métricas reales del modelo: Accuracy 96%, Precision 99%, Recall 93%, F1 96% (248.800 train / 62.200 test).

**Archivos:** `paquetes/prediccion/PrediccionRutas.py`, `paquetes/prediccion/PrediccionServicio.py`, `frontend/paginas/clinico/prediccion/index.html`

---

### ✅ Tarea 8: Pipeline ETL Visual

- [x] 8.1 Implementar `GET /api/pipeline/estado` que lista archivos `.parquet` en MinIO `stage/` con nombre, tamaño MB y fecha, ordenados por fecha descendente, retorna top 10.
- [x] 8.2 Frontend `pipeline_etl/index.html` con flujo visual 5 nodos: PocketBase → Airflow → MinIO → Parquet → FastAPI con iconos y colores diferenciados.
- [x] 8.3 4 KPI cards: Estado MinIO, Archivos Parquet, Último archivo, Última carga.
- [x] 8.4 Lista de archivos Parquet con nombre, tamaño MB y fecha.
- [x] 8.5 4 pasos del pipeline con descripción y comando técnico (GET, pd.DataFrame, put_object, GET estadísticas).
- [x] 8.6 Botón "Ejecutar pipeline" ejecuta 4 pasos en secuencia con estados visuales:
  - Paso 1: delay 1.2s simulando extracción PocketBase
  - Paso 2: delay 1.0s simulando transformación pandas
  - Paso 3: llama `GET /api/pipeline/estado` para verificar MinIO
  - Paso 4: llama `GET /api/registros/estadisticas` para verificar FastAPI
- [x] 8.7 Estados por paso: pending (—) → running (⏳ + animación pulse) → done (✓ verde) → error (✗ rojo).
- [x] 8.8 Función `resetSteps()` limpia todos los pasos antes de cada ejecución.

**Archivos:** `paquetes/pipeline_elt/PipelineEtlRutas.py`, `frontend/paginas/datos/pipeline_elt/index.html`

---

### ✅ Tarea 9: Control de Roles en Sidebar

- [x] 9.1 Función `aplicarRoles()` implementada en todas las páginas del frontend.
- [x] 9.2 Médico: oculta Dataset, Usuarios, Pipeline, Modelo ML, Reportes, Auditoría, Notificaciones, Configuración, Benchmarking, Integraciones.
- [x] 9.3 Analista: oculta Registros clínicos, Usuarios, Modelo ML, Reportes, Auditoría, Notificaciones, Configuración, Benchmarking, Integraciones.
- [x] 9.4 Administrador: ve todos los módulos.
- [x] 9.5 Comparación con `txt.includes(o)` en lugar de igualdad exacta para evitar problemas de encoding con tildes.
- [x] 9.6 `setTimeout(aplicarRoles, 50)` para evitar flash del sidebar al cargar.
- [x] 9.7 `aplicarRoles()` llamada dentro de `predecir()` para evitar flash al rerenderizar el DOM.

---

### ✅ Tarea 10: Conteo Eficiente con pyarrow

- [x] 10.1 Instalar pyarrow: ya incluido como dependencia de pandas.
- [x] 10.2 `GET /api/dataset/hechos` usa `pq.ParquetFile(BytesIO(...)).metadata.num_rows` para sumar total de registros de todos los parquets sin cargarlos en memoria.
- [x] 10.3 `GET /api/dataset/estadisticas` usa la misma técnica para el total; carga solo el parquet más reciente para columnas y conteo de diabetes.
- [x] 10.4 Frontend `dataset/index.html` muestra el total real en la KPI card "Fact diabetes" desde la respuesta del endpoint, no hardcodeado.

**Archivos:** `paquetes/dataset/DatasetRutas.py`

---

### ✅ Tarea 11: Reportes PDF

- [x] 11.1 Generación PDF con **fpdf2** (`ReportesServicio.generar_pdf`).
- [x] 11.2 `POST /api/reportes/generar` con filtros opcionales y persistencia MinIO `diabcare-app/reportes/`.
- [x] 11.3 `GET /api/reportes/` listado e historial.
- [x] 11.4 `GET /api/reportes/{nombre}` descarga con Authorization.
- [x] 11.5 Frontend `clinico/reportes/index.html` generar, listar y descargar.

**Archivos:** `paquetes/reportes/ReportesRutas.py`, `paquetes/reportes/ReportesServicio.py`, `frontend/paginas/clinico/reportes/index.html`

---

### ✅ Tarea 12: Auditoría

- [x] 12.1 `AuditoriaServicio.registrar()` → `diabcare-app/auditoria/eventos.parquet`.
- [x] 12.2 Registro en operaciones sensibles (auth, usuarios, módulos clave).
- [x] 12.3 `GET /api/auditoria/` con filtros y paginación.
- [x] 12.4 Frontend `gobierno/auditoria/index.html`.

**Archivos:** `paquetes/auditoria/AuditoriaRutas.py`, `paquetes/auditoria/AuditoriaServicio.py`, `frontend/paginas/gobierno/auditoria/index.html`

---

### ⏳ Tarea 13: Gestión de Versiones del Modelo ML

- [ ] 13.1 Modificar `PrediccionServicio.entrenar()` para guardar el modelo con timestamp: `diabcare-app/modelos/modelo_{timestamp}.pkl` además del `modelo_diabetes.pkl` activo.
- [ ] 13.2 Implementar `GET /api/modelo_ml/versiones` que liste todos los archivos `.pkl` en `diabcare-app/modelos/` con nombre, tamaño y fecha.
- [ ] 13.3 Implementar `PUT /api/modelo_ml/activar/{nombre}` que copie el archivo `{nombre}.pkl` como `modelo_diabetes.pkl` e invalide el `_modelo_cache`.
- [ ] 13.4 Frontend con historial de versiones, columnas nombre/fecha/tamaño, y botón "Activar" que llame al endpoint de activación con confirmación modal.

**Archivos:** `paquetes/modelo_ml/ModeloMlRutas.py`, `paquetes/prediccion/PrediccionServicio.py`, `frontend/paginas/datos/modelo_ml/index.html`

---

### ⏳ Tarea 14: Pruebas PBT (Property-Based Testing)

- [ ] 14.1 Instalar Hypothesis: `pip install hypothesis --break-system-packages`.
- [ ] 14.2 Crear `pruebas/test_autenticacion.py` — Property 1: credenciales incorrectas siempre retornan 401 usando `st.text()`.
- [ ] 14.3 Crear `pruebas/test_usuarios.py` — Property 2: round-trip creación de usuario; Property 3: email duplicado rechazado.
- [ ] 14.4 Crear `pruebas/test_dataset.py` — Property 4: invariante `con_diabetes + sin_diabetes == total`; Property 5: generación exacta de N filas.
- [ ] 14.5 Crear `pruebas/test_registros.py` — Property 6: todos los registros retornados satisfacen los filtros activos.
- [ ] 14.6 Crear `pruebas/test_prediccion.py` — Property 7: round-trip serialización del modelo; Property 8: probabilidad en [0,1] y riesgo consistente; Property 9: métricas en [0,1].
- [ ] 14.7 Ejecutar `pytest pruebas/ -v` y confirmar que todas las propiedades pasan con mínimo 100 ejemplos.

**Archivos:** `pruebas/test_autenticacion.py`, `pruebas/test_usuarios.py`, `pruebas/test_dataset.py`, `pruebas/test_registros.py`, `pruebas/test_prediccion.py`

---

### ⏳ Tarea 15: Pruebas de Integración

- [ ] 15.1 Crear `pruebas/test_integracion.py` con flujo completo: login → estadísticas → generar datos → verificar conteo actualizado.
- [ ] 15.2 Prueba de flujo de usuarios: crear → listar (verificar presencia) → cambiar rol → desactivar → listar (verificar activo=False).
- [ ] 15.3 Prueba de autenticación: token válido → acceso OK; token expirado → 401; rol incorrecto para módulo → 403.
- [ ] 15.4 Prueba de predicción: verificar estado (disponible=false) → entrenar → verificar estado (disponible=true) → predecir → verificar métricas en rango.
- [ ] 15.5 Ejecutar con MinIO real en `localhost:9000`; documentar en README los pasos para levantar el entorno de pruebas.

**Archivos:** `pruebas/test_integracion.py`

---

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": ["T1", "T6"],
      "description": "Infraestructura base: autenticación JWT y configuración del sistema"
    },
    {
      "wave": 2,
      "tasks": ["T2", "T3", "T4", "T8"],
      "description": "Módulos core que dependen de autenticación JWT (T1) y buckets MinIO (T6)"
    },
    {
      "wave": 3,
      "tasks": ["T5", "T9", "T10"],
      "description": "Estadísticas y optimizaciones que dependen de datos en MinIO (T3, T4)"
    },
    {
      "wave": 4,
      "tasks": ["T7"],
      "description": "Predicción ML que requiere datos de entrenamiento disponibles (T4, T5)"
    },
    {
      "wave": 5,
      "tasks": ["T11", "T12", "T13"],
      "description": "Reportes PDF (T3/T5), Auditoría (T1–T4) y Versiones ML (T7) — módulos pendientes independientes"
    },
    {
      "wave": 6,
      "tasks": ["T14", "T15"],
      "description": "Pruebas PBT e integración — requieren todas las implementaciones previas (T1–T13)"
    }
  ]
}
```

## Notes

### Estado de Implementación

| Fase | Estado |
|---|---|
| T1 — Autenticación JWT | ✅ Completado |
| T2 — Gestión de usuarios | ✅ Completado |
| T3 — Registros clínicos (CRUD) | ✅ Completado |
| T4 — Dataset y generador sintético | ✅ Completado |
| T5 — Estadísticas clínicas y Dashboard | ✅ Completado |
| T6 — Infraestructura y Sistema | ✅ Completado |
| T7 — Predicción ML | ✅ Completado |
| T8 — Pipeline ETL visual | ✅ Completado |
| T9 — Control de roles en sidebar | ✅ Completado |
| T10 — Conteo eficiente con pyarrow | ✅ Completado |
| T11 — Reportes PDF | ✅ Completado (fpdf2) |
| T12 — Auditoría | ✅ Completado |
| T13 — Gestión de versiones del Modelo ML | ⏳ Pendiente |
| T14 — Pruebas PBT | ⏳ Pendiente |
| T15 — Pruebas de integración | ⏳ Pendiente |

### Registro de Decisiones Técnicas

| Fecha | Decisión | Razón |
|---|---|---|
| 2026-05 | Frontend multi-página en lugar de SPA | Más simple de mantener, cada módulo es independiente |
| 2026-05 | Usuarios en Parquet MinIO en lugar de PocketBase | Consistencia con el resto del storage del sistema |
| 2026-05 | `/estadisticas` antes de `/{id}` en router | FastAPI evalúa rutas en orden, evita colisión de paths |
| 2026-05 | `--no-access-log` en Uvicorn | Reducir ruido en terminal de desarrollo |
| 2026-05 | Datos sintéticos en español | Consistencia con la interfaz en español |
| 2026-05 | SHA-256 para passwords | Simple para entorno académico, suficiente para el proyecto |
| 2026-05 | `warnings.filterwarnings` para JWT | Clave de 20 bytes genera warnings, suficiente para desarrollo |
| 2026-06 | RandomForest 100 árboles con n_jobs=-1 | Balance entre accuracy y tiempo de entrenamiento |
| 2026-06 | pickle para serializar modelo | Serialización nativa de Python, compatible con scikit-learn |
| 2026-06 | `_modelo_cache` en memoria | Evitar descarga repetida del modelo desde MinIO en cada predicción |
| 2026-06 | pyarrow.ParquetFile.metadata.num_rows | Lee solo el footer del parquet sin deserializar datos — conteo instantáneo |
| 2026-06 | `txt.includes(o)` para roles en sidebar | Evita problemas de encoding con tildes en nombres de módulos |
| 2026-06 | `setTimeout(aplicarRoles, 50)` | Evita flash del sidebar incorrecto al cargar la página |
| 2026-07 | PostgreSQL como BDR en docs TA11; MinIO columnar | Alineación enunciado Tarea 11 (informe simple vs compuesto) |
| 2026-07 | Reportes con fpdf2 (no reportlab) | Dependencia ya en requirements.txt |

---

## DiabCare Hospital — tareas v3

Las tareas T1–T10 del núcleo analytics siguen completadas. Reportes/auditoría/ML-versiones pueden existir en código aunque la tabla histórica las marcaba pendientes; el foco nuevo es **Hospital**.

### ✅ Tarea 16: Núcleo hospitalario P16–P20 + comorbilidades

- [x] 16.1 `ParquetStore` compartido (CRUD + soft-delete).
- [x] 16.2 Facturación: seguros, tarifario, facturas, pagos + UI principal.
- [x] 16.3 Farmacia B+C: catálogo, recetas, inventario, dispensar, compras, ventas, kardex, CxP, caja + UI principal.
- [x] 16.4 Laboratorio: pruebas, órdenes, resultados + UI.
- [x] 16.5 Urgencias: triage / atender + UI.
- [x] 16.6 Comorbilidades diabéticas + UI.
- [x] 16.7 RRHH/costeo: cargos, turnos, personal, productividad + UI.
- [x] 16.8 Roles `enfermero` / `farmaceutico` + `PERMISOS_MODULOS` + menú.
- [x] 16.9 Specs SDD en `specs/003-operativo/paquetes/P16`–`P20` y `P03-comorbilidades-ext`.
- [x] 16.10 Routers registrados en `Principal.py`.

### ✅ Tarea 17: Generador E2E

- [x] 17.1 `DatasetHospitalServicio` — seed `negocio/`.
- [x] 17.2 `DatasetFlujoServicio` — pacientes + citas + admisiones + registros enlazados.
- [x] 17.3 Integración en `POST /api/dataset/generar` (`incluir_hospital`) y `POST /api/dataset/hospital/generar`.
- [x] 17.4 UI generador: checkbox flujo + resumen pacientes/citas.
- [x] 17.5 Catálogo DWH: paths `negocio/` para tablas hospitalarias implementadas.
- [x] 17.6 Import lazy de sklearn en predicción (arranque sin bloquear).

### ✅ Tarea 18: UI secundaria hospitalaria

- [x] 18.1 Facturación: seguros, tarifario, pagos.
- [x] 18.2 Farmacia: proveedores, compras, ventas, kardex, CxP, cierre, dispensar.
- [x] 18.3 Laboratorio: captura de resultados en UI.
- [x] 18.4 Formularios por nombre (sin IDs crudos).

### ✅ Tarea 19: KPIs de negocio en dashboard

- [x] 19.1 Agregados margen, facturado, espera, productividad (`negocio/agg_*`).
- [x] 19.2 Widgets en dashboard / analítica.

### ✅ Tarea 20: Pruebas API hospitalarias (smoke)

- [x] 20.1 Smoke API hospitalaria en repo.
- [ ] 20.2 Casos RN detallados (factura, stock, triage, comorbilidad).

### ⏳ Tarea 21: Análisis táctico TA11 (documentación)

- [x] 21.1 Tabla departamental: objetivos | informe simple (PostgreSQL/BDR) | informe compuesto (MinIO).
- [x] 21.2 Catálogo de informes demostrables en app + guía de demo.
- [x] 21.3 CU-O04-B UML Mis citas; especificación Word/PDF fuera del repo.
- [ ] 21.4 Migración técnica BDR a PostgreSQL en runtime (opcional post-entrega).

### Orden de ejecución sugerido (resto)

```text
T20.2 (casos RN detallados) — opcional
```

### Estado resumen Hospital

| Tarea | Estado |
|-------|--------|
| T16 Núcleo P16–P20 | ✅ |
| T17 Generador E2E | ✅ |
| T18 UI secundaria | ✅ |
| T19 KPIs negocio | ✅ |
| T20 Tests hospital | ✅ parcial (smoke) |
| T21 TA11 táctica (docs) | ✅ doc / ⏳ Postgres runtime |
