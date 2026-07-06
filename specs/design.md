# Documento de Diseño — DiabCare Analytics v2.0

## Overview

DiabCare Analytics es una plataforma SaaS de análisis clínico de diabetes hospitalaria. El sistema lee archivos `.parquet` almacenados en MinIO, calcula estadísticas con pandas, entrena modelos de predicción con scikit-learn, y expone una interfaz web multi-página con autenticación JWT, gestión de usuarios, visualizaciones clínicas interactivas, predicción ML y monitoreo de pipeline ETL.

La arquitectura es de tres capas:
- **Presentación**: Frontend multi-página HTML/CSS/JS vanilla servido por FastAPI como archivos estáticos con rutas dinámicas.
- **Aplicación**: API REST con FastAPI + Uvicorn, autenticación JWT HS256, lógica de negocio en servicios Python separados por módulo.
- **Datos**: MinIO (object storage Parquet), PocketBase (fuente origen), Apache Airflow 2.9.1 Docker (orquestación ELT).

---

## Architecture

```mermaid
graph TD
    Browser["Navegador (HTML/JS vanilla)\nMulti-página — 8 páginas"]
    FastAPI["FastAPI + Uvicorn\nbackend/Principal.py\nlocalhost:8000"]
    JWT["JWT Auth\nHS256 · 8h\nDependencias.py"]
    MinIO["MinIO localhost:9000\ndiabetes-data/stage/*.parquet\ndiabcare-app/usuarios/usuarios.parquet\ndiabcare-app/modelos/modelo_diabetes.pkl"]
    PocketBase["PocketBase\nlocalhost:8090\nFuente de datos origen"]
    Airflow["Apache Airflow 2.9.1\nDocker Compose\nlocalhost:8080"]
    ML["scikit-learn\nRandomForest 100 árboles\npyarrow lectura eficiente"]

    Browser -- "fetch() + Bearer Token" --> FastAPI
    FastAPI -- "FileResponse HTML" --> Browser
    FastAPI -- "verificar_token()" --> JWT
    FastAPI -- "minio-py read/write/list" --> MinIO
    FastAPI -- "pd.concat + sklearn" --> ML
    PocketBase -- "API REST" --> Airflow
    Airflow -- "sube parquet stage/" --> MinIO
```

### Flujo de autenticación
1. Usuario envía `POST /api/auth/login` con email y password.
2. Backend busca usuario en `diabcare-app/usuarios/usuarios.parquet`, compara SHA-256 del password.
3. Si válido, genera JWT con `sub`, `email`, `rol`, `exp` (8h) usando `python-jose` HS256.
4. Frontend almacena token en `localStorage` y objeto usuario completo, redirige al Dashboard.
5. Cada request incluye `Authorization: Bearer {token}` en headers fetch.
6. `Dependencias.py::verificar_token()` decodifica y valida el token antes de cada endpoint protegido.

### Flujo de datos clínicos (ELT)
1. Airflow extrae datos de PocketBase y genera archivos `.parquet` en MinIO `diabetes-data/stage/`.
2. El generador sintético (`DatasetServicio.generar_y_subir()`) crea registros y los sube a `stage/`.
3. `RegistrosClinicosServicio._extraer()` lista todos los `.parquet` en `stage/` con `minio.list_objects()`, los concatena con `pd.concat()` y retorna un DataFrame unificado.
4. Los endpoints de estadísticas calculan métricas desde ese DataFrame con pandas en memoria.
5. Para conteo rápido sin cargar datos: `pyarrow.parquet.ParquetFile(BytesIO(...)).metadata.num_rows`.

### Flujo de predicción ML
1. `POST /api/prediccion/entrenar` carga el DataFrame completo, entrena RandomForest con split 80/20.
2. Modelo y métricas se serializan con pickle y se suben a MinIO `diabcare-app/modelos/modelo_diabetes.pkl`.
3. `_modelo_cache` almacena el modelo en memoria tras la primera carga.
4. `POST /api/prediccion/` recibe 6 features, llama `modelo.predict()` y `predict_proba()`, retorna diagnóstico + probabilidad + nivel de riesgo.

---

## Estructura de Archivos

```
diabcare/
├── backend/
│   ├── Principal.py
│   ├── nucleo/
│   │   ├── modelos/              ← DWH hecho/dimensiones/catálogo
│   │   └── utilidades/           ← Dependencias.py, JWT, Parquet, logs
│   └── paquetes/                 ← Un folder por paquete (Rutas + Servicio)
│       ├── autenticacion/
│       ├── usuarios/
│       ├── registros_clinicos/
│       ├── dataset/
│       ├── prediccion/
│       ├── reportes/
│       ├── pipeline_elt/
│       ├── auditoria/
│       ├── configuracion/
│       ├── modelo_ml/
│       └── clinico/
│           ├── pacientes/
│           ├── admisiones/
│           └── citas/
│
├── frontend/
│   ├── estaticos/                ← estilos.css, navegacion.js, api.js
│   └── paginas/
│       ├── seguridad/            ← autenticacion, usuarios, perfil
│       ├── clinico/              ← analisis, registros, prediccion, reportes, …
│       ├── datos/                ← dataset, pipeline_elt, modelo_ml
│       └── gobierno/             ← auditoria, configuracion
│
├── specs/                        ← Especificaciones SDD
├── pruebas/                      ← pytest
└── docker-compose.yaml
```

---

## Components and Interfaces

### Backend — Endpoints completos

| Módulo | Endpoint | Método | Auth | Descripción |
|---|---|---|---|---|
| Auth | `/api/auth/login` | POST | No | Login JWT |
| Auth | `/api/auth/logout` | POST | Sí | Cierre de sesión |
| Auth | `/api/auth/cambiar-password` | PUT | Sí | Cambio de contraseña |
| Auth | `/api/auth/recuperar` | POST | No | Enviar código reset |
| Auth | `/api/auth/resetear` | POST | No | Reset con código |
| Usuarios | `/api/usuarios/` | GET | Admin | Listar usuarios |
| Usuarios | `/api/usuarios/` | POST | Admin | Crear usuario |
| Usuarios | `/api/usuarios/{id}/rol` | PUT | Admin | Cambiar rol |
| Usuarios | `/api/usuarios/{id}` | DELETE | Admin | Desactivar usuario |
| Registros | `/api/registros/estadisticas` | GET | Auth | Estadísticas completas (ANTES de /{id}) |
| Registros | `/api/registros/` | GET | Auth | Listar con paginación |
| Registros | `/api/registros/buscar` | GET | Auth | Filtrar registros |
| Registros | `/api/registros/` | POST | Auth | Crear registro |
| Registros | `/api/registros/{id}` | PUT/DELETE | Auth | Editar/eliminar |
| Dataset | `/api/dataset/hechos` | GET | Auth | Tabla hechos paginada + total pyarrow |
| Dataset | `/api/dataset/dimension/{nombre}` | GET | Auth | Dimensiones |
| Dataset | `/api/dataset/generar` | POST | Auth | Generar datos sintéticos |
| Dataset | `/api/dataset/estadisticas` | GET | Auth | Stats rápidas con pyarrow |
| Predicción | `/api/prediccion/entrenar` | POST | Auth | Entrenar modelo RandomForest |
| Predicción | `/api/prediccion/` | POST | Auth | Predecir diabetes individual |
| Predicción | `/api/prediccion/metricas` | GET | Auth | Accuracy, precision, recall, F1 |
| Predicción | `/api/prediccion/estado` | GET | Auth | Verificar si modelo disponible |
| Pipeline | `/api/pipeline/estado` | GET | Auth | Listar archivos Parquet en MinIO stage/ |

### Servicio de predicción — `PrediccionServicio.py`

```python
FEATURES = ["age", "bmi", "hbA1c_level", "blood_glucose_level", "hypertension", "heart_disease"]
_modelo_cache = {"modelo": None, "metricas": None}

# entrenar(): carga DataFrame completo → RandomForest(n_estimators=100) → pickle → MinIO
# predecir(datos): carga modelo desde cache → predict() + predict_proba() → riesgo según probabilidad
# obtener_metricas(): retorna metricas desde cache o carga desde MinIO
# modelo_disponible(): True si modelo existe en MinIO
```

### Servicio de estadísticas — `RegistrosClinicosServicio._extraer()`

```python
# Lista todos los .parquet en stage/ → pd.concat() → DataFrame unificado en memoria
# Estadísticas calculadas:
# - genero: value_counts()
# - tabaquismo: groupby smoking_history × diabetes
# - razas: sum() de flags race_* por grupo diabetes
# - edad: pd.cut([<20, 20-30, 31-40, 41-50, 51-60, 61-70, 70+])
# - promedios: mean() de bmi/hbA1c_level/blood_glucose_level por grupo diabetes
# - comorbilidades: cruce hypertension/heart_disease × diabetes
# - ubicaciones: top 10 value_counts() de location
# - tendencia: groupby year → count + sum diabetes
```

### Conteo eficiente con pyarrow — `DatasetRutas.py`

```python
import pyarrow.parquet as pq
# Lee solo el footer del parquet sin deserializar datos:
pf = pq.ParquetFile(io.BytesIO(obj.read()))
total += pf.metadata.num_rows
# Resultado: conteo de 600k+ registros en < 2 segundos
```

### Autenticación — `Dependencias.py`

```python
PERMISOS_MODULOS = {
    "usuarios":      ["administrador"],
    "configuracion": ["administrador"],
    "auditoria":     ["administrador"],
    "pacientes":     ["administrador", "medico"],
    "admisiones":    ["administrador"],
    "citas":         ["administrador"],
    "registros":     ["administrador", "medico"],
    "analisis":      ["administrador", "medico"],
    "prediccion":    ["administrador", "medico"],
    "reportes":      ["administrador", "medico"],
    "dataset":       ["administrador", "analista"],
    "pipeline_etl":  ["administrador", "analista"],
    "modelo_ml":     ["administrador", "analista"],
    "integraciones": ["administrador", "analista"],
    "notificaciones":["administrador", "medico", "analista"],
}
```

### Control de roles en frontend — `aplicarRoles()`

Función presente en todas las páginas del frontend:

```javascript
function aplicarRoles() {
  const u = JSON.parse(localStorage.getItem('usuario') || '{}');
  const rol = u.rol || '';
  const OCULTAR = {
    'medico':   ['Dataset','Usuarios','Pipeline','Modelo','Reportes','Auditor','Notificac','Configur','Benchmark','Integrac'],
    'analista': ['Registros','Usuarios','Modelo','Reportes','Auditor','Notificac','Configur','Benchmark','Integrac'],
  };
  const ocultar = OCULTAR[rol] || [];
  document.querySelectorAll('.nav-group').forEach(g => {
    const label = g.querySelector('.nav-group-label');
    if (!label) return;
    const txt = label.textContent.trim();
    if (ocultar.some(o => txt.includes(o))) g.style.display = 'none';
  });
}
// Llamar con setTimeout(aplicarRoles, 50) al cargar
// Y dentro de funciones que rerenderizen el DOM (ej. dentro de predecir())
```

---

## Frontend — Design System

### Variables CSS (`estilos.css`)

```css
:root {
  --bg: #09090f;
  --bg2: #0d0d15;
  --bg3: #111118;
  --border: rgba(255,255,255,0.07);
  --accent: #2563eb;
  --accent2: #3b82f6;
  --green: #22c55e;
  --red: #ef4444;
  --amber: #f59e0b;
  --mono: 'JetBrains Mono', monospace;
}
```

### Componentes compartidos
- `.sidebar` + `.nav-group` + `.nav-sub-item` — navegación colapsable con `toggle()`
- `.stat-card` + `.stat-value` — KPI cards con colores semánticos
- `.tabla-card` + `table` — tablas de datos con hover
- `.btn` + `.btn-primary` + `.btn-ghost` + `.btn-sm` — botones
- `.overlay` + `.modal` — modales con animación
- `.toast` — notificaciones flotantes con auto-dismiss 3 segundos
- `.spinner` — indicador de carga
- `.user-row-wrap` + `.btn-logout` — fila de usuario con botón cerrar sesión (icono ⏻)

### Páginas y su fuente de datos

| Página | Ruta | Endpoints consumidos |
|---|---|---|
| Login | `/paginas/seguridad/autenticacion/index.html` | `POST /api/auth/login` |
| Dashboard | `/paginas/clinico/analisis/index.html` | `GET /api/registros/estadisticas`, `GET /api/dataset/estadisticas` |
| Estadísticas | `/paginas/estadisticas/index.html` | `GET /api/registros/estadisticas` |
| Registros | `/paginas/registros_clinicos/index.html` | `GET /api/registros/`, `GET /api/registros/buscar`, `GET /api/registros/estadisticas` |
| Ver tablas | `/paginas/dataset/index.html` | `GET /api/dataset/hechos`, `GET /api/dataset/dimension/*` |
| Generador | `/paginas/dataset/generador.html` | `POST /api/dataset/generar` |
| Usuarios | `/paginas/seguridad/usuarios/index.html` | `GET/POST/PUT/DELETE /api/usuarios/` |
| Predicción ML | `/paginas/prediccion/index.html` | `POST /api/prediccion/entrenar`, `POST /api/prediccion/`, `GET /api/prediccion/metricas`, `GET /api/prediccion/estado` |
| Pipeline ETL | `/paginas/pipeline_etl/index.html` | `GET /api/pipeline/estado`, `GET /api/registros/estadisticas` |

---

## Data Models

### Dataset clínico (Parquet en MinIO `diabetes-data/stage/`)

| Columna | Tipo | Descripción |
|---|---|---|
| `gender` | string | Masculino / Femenino / Otro |
| `age` | float | Edad del paciente [1-80] |
| `location` | string | Ciudad en español (Alabama, California...) |
| `year` | int | Año del registro |
| `hypertension` | int (0/1) | Hipertensión preexistente |
| `heart_disease` | int (0/1) | Cardiopatía preexistente |
| `smoking_history` | string | nunca / actual / no actual / Sin información |
| `bmi` | float | Índice de masa corporal [15-45] |
| `hbA1c_level` | float | Hemoglobina glicosilada [3.5-9.0] |
| `blood_glucose_level` | int | Glucosa en sangre mg/dL [80-300] |
| `diabetes` | int (0/1) | Diagnóstico de diabetes |
| `race_AfricanAmerican` | int (0/1) | Indicador de raza |
| `race_Asian` | int (0/1) | Indicador de raza |
| `race_Caucasian` | int (0/1) | Indicador de raza |
| `race_Hispanic` | int (0/1) | Indicador de raza |
| `race_Other` | int (0/1) | Indicador de raza |

### Usuarios (Parquet en MinIO `diabcare-app/usuarios/usuarios.parquet`)

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | string (UUID) | Identificador único |
| `nombre` | string | Nombre completo |
| `email` | string | Email único |
| `password_hash` | string | SHA-256 del password |
| `rol` | string | administrador / medico / analista |
| `activo` | bool | Estado del usuario (False = desactivado) |
| `creado_en` | string (ISO) | Fecha de creación |

### Modelo ML (pickle en MinIO `diabcare-app/modelos/modelo_diabetes.pkl`)

```python
{
    "modelo": RandomForestClassifier,  # 100 árboles, random_state=42, n_jobs=-1
    "metricas": {
        "accuracy": float,
        "precision": float,
        "recall": float,
        "f1": float,
        "registros_entrenamiento": int,
        "registros_prueba": int
    }
}
```

---

## Correctness Properties

*Una propiedad es una característica o comportamiento que debe ser verdadero en todas las ejecuciones válidas del sistema — esencialmente, un enunciado formal sobre lo que el sistema debe hacer. Las propiedades sirven como puente entre las especificaciones legibles por humanos y las garantías de corrección verificables automáticamente.*

### Property 1: Credenciales incorrectas siempre reciben 401

*For any* par (email, password) que no coincida con las credenciales almacenadas de ningún usuario activo, el endpoint `POST /api/auth/login` debe retornar HTTP 401.

**Validates: Requirements 1.3**

### Property 2: Creación de usuario es un round-trip

*For any* conjunto de datos de usuario válidos (nombre, email, password, rol), crear el usuario y luego recuperarlo con `GET /api/usuarios/` debe retornar un objeto con el mismo nombre, email y rol, sin exponer el password_hash.

**Validates: Requirements 2.1, 2.2, 2.7**

### Property 3: Email duplicado siempre es rechazado

*For any* email, intentar crear dos usuarios con ese mismo email debe resultar en HTTP 400 en la segunda operación, sin importar cuáles sean los demás campos del segundo usuario.

**Validates: Requirements 2.3**

### Property 4: Invariante de conteo de estadísticas

*For any* dataset cargado desde MinIO, la suma `con_diabetes + sin_diabetes` debe ser siempre igual al campo `total` retornado por `GET /api/dataset/estadisticas` y `GET /api/registros/estadisticas`.

**Validates: Requirements 3.3, 5.1, 5.2**

### Property 5: Generación de datos es exacta

*For any* cantidad `N` solicitada al endpoint `POST /api/dataset/generar`, el archivo Parquet resultante subido a MinIO debe contener exactamente `N` filas, verificable vía `pyarrow.parquet.ParquetFile.metadata.num_rows`.

**Validates: Requirements 3.4, 3.5**

### Property 6: Filtros de registros son consistentes

*For any* combinación de filtros aplicada a `GET /api/registros/buscar` (diabetes, gender, location, age_min, age_max), todos los registros retornados deben satisfacer todos los filtros activos sin excepción.

**Validates: Requirements 4.2**

### Property 7: Round-trip de serialización del modelo ML

*For any* dataset de entrenamiento, el modelo entrenado, serializado con pickle y subido a MinIO, al descargarse y deserializarse debe producir predicciones idénticas a las del modelo original en memoria para cualquier vector de entrada.

**Validates: Requirements 7.1, 7.2**

### Property 8: Probabilidad y clasificación de riesgo son consistentes

*For any* vector de entrada válido con los 6 features clínicos, la probabilidad retornada por `POST /api/prediccion/` debe estar en el rango [0.0, 1.0], y el nivel de riesgo debe ser consistente con los umbrales definidos (Alto ≥ 0.7, Medio ≥ 0.4, Bajo < 0.4).

**Validates: Requirements 7.3**

### Property 9: Métricas del modelo están en rango válido

*For any* modelo entrenado sobre cualquier dataset clínico, las métricas retornadas por `GET /api/prediccion/metricas` (accuracy, precision, recall, f1) deben estar todas en el rango [0.0, 1.0].

**Validates: Requirements 7.4**

---

## Error Handling

| Situación | HTTP | Detail |
|---|---|---|
| Credenciales incorrectas | 401 | "Credenciales incorrectas" |
| Token ausente | 401 | "Token requerido" |
| Token expirado | 401 | "Token expirado" |
| Rol no reconocido | 401 | "Rol del token no reconocido" |
| Sin permisos para módulo | 403 | "Su rol '{rol}' no tiene acceso al módulo '{modulo}'" |
| Usuario no encontrado | 404 | "Usuario no encontrado" |
| Email ya registrado | 400 | "Email ya registrado" |
| Registro no encontrado | 404 | "Registro no encontrado" |
| Modelo no entrenado | 200 | `{"error": "Modelo no entrenado. Llama primero a POST /api/prediccion/entrenar"}` |
| MinIO sin archivos | 200 | DataFrame vacío, retorna lista vacía o total 0 |

---

## Testing Strategy

### Enfoque dual: pruebas unitarias + pruebas basadas en propiedades

La estrategia combina pruebas de ejemplo para casos concretos con pruebas basadas en propiedades (PBT) para validar invariantes universales. Se utiliza **Hypothesis** como librería PBT para Python, configurada con mínimo 100 iteraciones por propiedad.

### Pruebas basadas en propiedades (Hypothesis)

Cada propiedad del documento se implementa como un test de Hypothesis con el decorador `@given`. Se etiquetan con el formato:
`# Feature: diabcare-analytics, Property {N}: {descripción}`

| Propiedad | Test | Estrategia de generación |
|---|---|---|
| Property 1: Credenciales incorrectas → 401 | `test_invalid_credentials_always_401` | `st.text()` para email y password no registrados |
| Property 2: Round-trip creación de usuario | `test_user_creation_roundtrip` | `st.builds(UsuarioData)` con campos aleatorios válidos |
| Property 3: Email duplicado → 400 | `test_duplicate_email_rejected` | `st.emails()` para email base |
| Property 4: Invariante de conteo | `test_stats_count_invariant` | DataFrames sintéticos con `st.integers(min_value=0)` |
| Property 5: Generación exacta de N filas | `test_dataset_generation_exact_count` | `st.integers(min_value=1, max_value=1000)` |
| Property 6: Filtros consistentes | `test_filter_results_satisfy_filters` | `st.from_type(FiltroRegistros)` |
| Property 7: Round-trip serialización ML | `test_model_serialization_roundtrip` | DataFrames de entrenamiento sintéticos |
| Property 8: Probabilidad y riesgo coherentes | `test_prediction_probability_range` | `st.builds(InputPrediccion)` con rangos clínicos válidos |
| Property 9: Métricas en rango válido | `test_metrics_in_valid_range` | DataFrames con distribuciones variables |

Ejemplo de estructura de test:

```python
from hypothesis import given, settings
import hypothesis.strategies as st

# Feature: diabcare-analytics, Property 4: Invariante de conteo de estadísticas
@given(st.integers(min_value=0, max_value=10000),
       st.integers(min_value=0, max_value=10000))
@settings(max_examples=100)
def test_stats_count_invariant(con_diabetes, sin_diabetes):
    df = crear_dataframe_sintetico(con_diabetes, sin_diabetes)
    stats = calcular_estadisticas(df)
    assert stats["con_diabetes"] + stats["sin_diabetes"] == stats["total"]
```

### Pruebas unitarias de ejemplo

Se escriben para casos concretos que complementan las propiedades:

- **Autenticación**: Login exitoso con credenciales del admin por defecto; logout retorna confirmación.
- **Usuarios**: Cambio de rol, desactivación de usuario (activo=False), listado sin exponer password_hash.
- **Dataset**: Respuesta de `GET /api/dataset/hechos` incluye campos `total` y `registros`; dimensiones retornan las columnas esperadas.
- **Predicción**: Respuesta de `POST /api/prediccion/` incluye `diagnostico`, `resultado`, `probabilidad` y `riesgo`; `GET /api/prediccion/estado` retorna False si no existe modelo.
- **Pipeline**: `GET /api/pipeline/estado` retorna estructura con `estado`, `total_archivos`, `archivos`.
- **Frontend (ejemplo)**: Página de login contiene formulario con campos email y password.

### Pruebas de integración

Se usan 1-3 ejemplos representativos para operaciones con MinIO y Airflow:

- Verificar que `inicializar_buckets()` crea los buckets si no existen.
- Verificar que `POST /api/dataset/generar` sube efectivamente un archivo Parquet a MinIO `stage/`.
- Verificar que `GET /api/pipeline/estado` lista correctamente archivos reales en MinIO.
- Verificar que el flujo completo entrenamiento → predicción funciona con datos reales.

### Cobertura objetivo

| Módulo | Tipo de test prioritario |
|---|---|
| `AutenticacionServicio` | Property (credenciales) + Example (login exitoso) |
| `UsuariosServicio` | Property (round-trip, email único) |
| `DatasetServicio` | Property (conteo exacto, invariante estadísticas) |
| `RegistrosClinicosServicio` | Property (filtros consistentes, invariante conteo) |
| `PrediccionServicio` | Property (serialización, probabilidad, métricas) |
| `ConfiguracionClienteMinio` | Integration (buckets, conectividad) |
| Frontend páginas | Example (estructura HTML, endpoints consumidos) |
