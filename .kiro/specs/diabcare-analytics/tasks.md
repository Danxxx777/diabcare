# Tareas de Implementación — DiabCare Analytics v2.0

## Estado General

| Fase | Estado |
|---|---|
| P1 — Autenticación JWT | ✅ Completado |
| P2 — Gestión de usuarios | ✅ Completado |
| P3 — Registros clínicos (CRUD) | ✅ Completado |
| P4 — Dataset y generador sintético | ✅ Completado |
| P5 — Estadísticas clínicas | ✅ Completado |
| P6 — Dashboard ejecutivo | ✅ Completado |
| P7 — Frontend multi-página | ✅ Completado |
| P8 — Predicción ML | ⏳ Pendiente |
| P9 — Pipeline ETL visual | ⏳ Pendiente |
| P10 — Modelo ML | ⏳ Pendiente |
| P11 — Reportes | ⏳ Pendiente |
| P12 — Auditoría | ⏳ Pendiente |
| P13 — Benchmarking | ⏳ Pendiente |
| P14 — Pruebas PBT | ⏳ Pendiente |
| P15 — Pruebas integración | ⏳ Pendiente |

---

## Tareas Completadas

### ✅ Tarea 1: Autenticación JWT

- [x] 1.1 Implementar `POST /api/auth/login` con validación de credenciales y generación de JWT (HS256, 8h).
- [x] 1.2 Implementar `verificar_token()` en `AutenticacionServicio.py` con validación de rol.
- [x] 1.3 Implementar `Dependencias.py` con `require_auth`, `require_admin`, `require_modulo()`.
- [x] 1.4 Definir `PERMISOS_MODULOS` con restricciones por rol para 12 módulos.
- [x] 1.5 Implementar usuario admin por defecto `admin@diabcare.com / Admin2026*`.
- [x] 1.6 Implementar `POST /api/auth/recuperar` y `POST /api/auth/resetear` para reset de password.
- [x] 1.7 Implementar `PUT /api/auth/cambiar-password` con validación de password actual.
- [x] 1.8 Frontend login con validación de campos, spinner y redirección al Dashboard.

**Archivos:** `api/autenticacion/AutenticacionRutas.py`, `servicios/autenticacion/AutenticacionServicio.py`, `utilidades/Dependencias.py`

---

### ✅ Tarea 2: Gestión de Usuarios

- [x] 2.1 Implementar `GET /api/usuarios/` retornando lista sin password_hash.
- [x] 2.2 Implementar `POST /api/usuarios/` con validación de email único y hash SHA-256.
- [x] 2.3 Implementar `PUT /api/usuarios/{id}/rol` para cambio de rol.
- [x] 2.4 Implementar `DELETE /api/usuarios/{id}` como desactivación (activo=False).
- [x] 2.5 Implementar `UsuariosServicio.py` con persistencia en `diabcare-app/usuarios/usuarios.parquet`.
- [x] 2.6 Frontend gestión con KPI cards (total, activos, inactivos, admins).
- [x] 2.7 Frontend con búsqueda en tiempo real por nombre/email.
- [x] 2.8 Frontend con modal para crear usuario y cambiar rol.
- [x] 2.9 Frontend con avatares de inicial y colores por índice.
- [x] 2.10 Corrección de `rol: null` en usuario admin via script Python directo.

**Archivos:** `api/usuarios/UsuariosRutas.py`, `servicios/usuarios/UsuariosServicio.py`, `frontend/paginas/usuarios/index.html`

---

### ✅ Tarea 3: Registros Clínicos

- [x] 3.1 Implementar `_extraer()` que concatena todos los `.parquet` de `stage/` en un DataFrame unificado.
- [x] 3.2 Implementar `GET /api/registros/` con paginación skip/limit.
- [x] 3.3 Implementar `GET /api/registros/buscar` con filtros: diabetes, gender, location, age_min, age_max.
- [x] 3.4 Implementar `POST /api/registros/`, `PUT /api/registros/{id}`, `DELETE /api/registros/{id}`.
- [x] 3.5 Implementar `GET /api/registros/estadisticas` con cálculo completo desde DataFrame.
- [x] 3.6 Estadísticas incluyen: genero, tabaquismo, razas, edad (rangos), promedios, comorbilidades, ubicaciones, tendencia.
- [x] 3.7 Frontend consulta con tabla paginada y filtros.

**Nota:** La ruta `/estadisticas` debe declararse ANTES de `/{encounter_id}` en el router para evitar colisión.

**Archivos:** `api/registros_clinicos/RegistrosClinicosRutas.py`, `servicios/registros_clinicos/RegistrosClinicosServicio.py`, `frontend/paginas/registros_clinicos/index.html`

---

### ✅ Tarea 4: Dataset y Generador Sintético

- [x] 4.1 Implementar `GET /api/dataset/hechos` con paginación.
- [x] 4.2 Implementar `GET /api/dataset/dimension/{nombre}` para paciente, ubicacion, raza, condicion.
- [x] 4.3 Implementar `POST /api/dataset/generar` con parámetros `cantidad` y `year`.
- [x] 4.4 `generar_registro()` genera campos en español (género, tabaquismo, ubicaciones).
- [x] 4.5 Generador sube archivo Parquet a MinIO con nombre `sinteticos_{year}_{timestamp}.parquet`.
- [x] 4.6 Frontend generador con presets 1K/10K/50K/100K/500K.
- [x] 4.7 Frontend con barra de progreso animada y pasos: Generando → Parquet → MinIO → Completado.
- [x] 4.8 Frontend muestra card de resultado con registros, año, formato y nombre de archivo.
- [x] 4.9 Frontend ver tablas separado del generador en páginas independientes.

**Archivos:** `api/dataset/DatasetRutas.py`, `servicios/dataset/DatasetServicio.py`, `frontend/paginas/dataset/index.html`, `frontend/paginas/dataset/generador.html`

---

### ✅ Tarea 5: Estadísticas y Dashboard

- [x] 5.1 Dashboard consume `/api/registros/estadisticas` y `/api/dataset/estadisticas`.
- [x] 5.2 Dashboard muestra 4 KPI cards con barras de color inferiores.
- [x] 5.3 Dashboard muestra donut compacto con porcentajes.
- [x] 5.4 Dashboard muestra 4 accesos rápidos con iconos.
- [x] 5.5 Dashboard genera alertas clínicas dinámicas (prevalencia, HbA1c, BMI, volumen).
- [x] 5.6 Dashboard muestra promedios clínicos con badges.
- [x] 5.7 Dashboard muestra top 6 ubicaciones con barras proporcionales.
- [x] 5.8 Dashboard muestra estado del sistema con badges ok/warn.
- [x] 5.9 Dashboard muestra archivos MinIO con columnas del dataset.
- [x] 5.10 Página estadísticas con 10+ gráficas reales (Chart.js): donut, género, comorbilidades, edad, raza, tabaquismo, ubicaciones, tendencia.
- [x] 5.11 KPI clínicos secundarios con BMI, HbA1c y glucosa promedio con/sin diabetes.
- [x] 5.12 Barras comparativas inline con animación CSS.

**Archivos:** `frontend/paginas/analisis/index.html`, `frontend/paginas/estadisticas/index.html`

---

### ✅ Tarea 6: Infraestructura y Sistema

- [x] 6.1 `Principal.py` sirve frontend multi-página con ruta dinámica `/{modulo}/{archivo}`.
- [x] 6.2 `inicializar_buckets()` crea buckets MinIO en startup si no existen.
- [x] 6.3 `inicializar_admin()` crea usuario admin por defecto si tabla vacía.
- [x] 6.4 `warnings.filterwarnings("ignore")` para suprimir logs de JWT key length.
- [x] 6.5 `GET /favicon.ico` retorna 204 para suprimir logs de 404.
- [x] 6.6 Uvicorn con `--no-access-log` para logs limpios en desarrollo.
- [x] 6.7 `estilos.css` como design system compartido con variables CSS y componentes reutilizables.
- [x] 6.8 Sidebar consistente en todas las páginas con `.user-row-wrap` + `.btn-logout`.
- [x] 6.9 `ANALYTICS v2.0` removido del logo en todas las páginas.

**Archivos:** `Principal.py`, `servicios/configuracion/ConfiguracionClienteMinio.py`, `frontend/estaticos/estilos.css`

---

## Tareas Pendientes

### ⏳ Tarea 7: Predicción ML

- [ ] 7.1 Entrenar modelo scikit-learn (RandomForest o LogisticRegression) con el dataset.
- [ ] 7.2 Guardar modelo en MinIO `diabcare-app/modelos/modelo_diabetes.pkl`.
- [ ] 7.3 Implementar `POST /api/prediccion/` que reciba campos clínicos y retorne probabilidad de diabetes.
- [ ] 7.4 Frontend con formulario de predicción individual y resultado visual.
- [ ] 7.5 Métricas del modelo: accuracy, precision, recall, F1 en `/api/prediccion/metricas`.

**Archivos:** `api/prediccion/PrediccionRutas.py`, `servicios/prediccion/`, `frontend/paginas/prediccion/index.html`

---

### ⏳ Tarea 8: Pipeline ETL Visual

- [ ] 8.1 Implementar endpoint que retorne estado del DAG de Airflow.
- [ ] 8.2 Frontend con visualización del flujo PocketBase → Airflow → MinIO.
- [ ] 8.3 Botón para disparar ejecución manual del DAG.
- [ ] 8.4 Historial de ejecuciones con estado y timestamp.

---

### ⏳ Tarea 9: Reportes

- [ ] 9.1 Implementar `POST /api/reportes/generar` que genere PDF con estadísticas.
- [ ] 9.2 Subir PDF generado a MinIO `diabcare-app/reportes/`.
- [ ] 9.3 Implementar `GET /api/reportes/` que liste reportes disponibles.
- [ ] 9.4 Frontend con generación y descarga de reportes.

---

### ⏳ Tarea 10: Auditoría

- [ ] 10.1 Registrar en MinIO cada operación CRUD con usuario, acción, timestamp y datos afectados.
- [ ] 10.2 Implementar `GET /api/auditoria/` con filtros por usuario, fecha y tipo de acción.
- [ ] 10.3 Frontend con tabla de auditoría paginada.

---

### ⏳ Tarea 11: Pruebas PBT (Property-Based Testing)

- [ ] 11.1 Crear `pruebas/test_unitario.py` con Hypothesis para endpoints de estadísticas.
- [ ] 11.2 Crear `pruebas/test_tablas.py` para validar estructura de DataFrames generados.
- [ ] 11.3 Crear `pruebas/test_stats_servicio.py` para estadísticas con DataFrames aleatorios.
- [ ] 11.4 Crear `pruebas/test_charts_servicio.py` para validar gráficas con datos variados.
- [ ] 11.5 Crear `pruebas/test_empresa_servicio.py` para datos corporativos.
- [ ] 11.6 Ejecutar `pytest pruebas/ -v` y confirmar que todos pasan.

---

### ⏳ Tarea 12: Pruebas de Integración

- [ ] 12.1 Crear `pruebas/test_integracion.py` con flujo completo: login → estadísticas → generar datos → verificar.
- [ ] 12.2 Prueba de flujo de usuarios: crear → listar → cambiar rol → desactivar.
- [ ] 12.3 Prueba de autenticación: token válido → acceso; token expirado → 401; rol incorrecto → 403.
- [ ] 12.4 Ejecutar con MinIO real en `localhost:9000`.

---

## Registro de Decisiones Técnicas

| Fecha | Decisión | Razón |
|---|---|---|
| 2026-05 | Frontend multi-página en lugar de SPA | Más simple de mantener, cada módulo es independiente |
| 2026-05 | Usuarios en Parquet MinIO en lugar de PocketBase | Consistencia con el resto del storage del sistema |
| 2026-05 | `/estadisticas` antes de `/{id}` en router | FastAPI evalúa rutas en orden, evita colisión de paths |
| 2026-05 | `--no-access-log` en Uvicorn | Reducir ruido en terminal de desarrollo |
| 2026-05 | Datos sintéticos en español | Consistencia con la interfaz en español |
| 2026-05 | SHA-256 para passwords | Simple para entorno académico, suficiente para el proyecto |
| 2026-05 | `warnings.filterwarnings` para JWT | Clave de 20 bytes genera warnings, suficiente para desarrollo |
