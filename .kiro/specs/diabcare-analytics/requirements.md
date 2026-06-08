# Documento de Requisitos — DiabCare Analytics v2.0

## Introducción

DiabCare Analytics es una plataforma SaaS académica (6to semestre — Construcción del Software) para la gestión y análisis de datos clínicos de diabetes hospitalaria. El sistema lee archivos `.parquet` almacenados en MinIO, genera estadísticas clínicas con pandas, expone visualizaciones analíticas, gestión de usuarios, registros clínicos, predicción ML y pipeline ELT con autenticación JWT por roles.

**Stack tecnológico:** FastAPI + Python 3.14 (backend), MinIO (object storage), pandas (transformación ELT), scikit-learn (ML), pyarrow (lectura eficiente de Parquet), HTML/CSS/JS vanilla (frontend multi-página), PocketBase (fuente origen), Apache Airflow 2.9.1 Docker (orquestación), Uvicorn (servidor).

---

## Glosario

- **Sistema**: La aplicación web DiabCare Analytics (backend FastAPI + frontend HTML/JS multi-página).
- **API**: Endpoints REST expuestos por el backend FastAPI en `localhost:8000`.
- **MinIO**: Object storage local en `localhost:9000`. Bucket principal: `diabetes-data`, prefijo `stage/`. Bucket app: `diabcare-app`.
- **Dataset**: DataFrame de pandas cargado concatenando todos los `.parquet` en MinIO `stage/`, con registros clínicos de diabetes sintéticos.
- **Token JWT**: Token de autenticación generado al iniciar sesión, válido por 8 horas, almacenado en `localStorage`.
- **Roles**: `administrador`, `medico`, `analista`. Cada rol tiene acceso restringido a módulos específicos del sidebar y de la API.
- **PocketBase**: Base de datos en `localhost:8090` que almacena datos origen del pipeline.
- **Airflow**: Orquestador de pipelines ELT en Docker Compose que mueve datos de PocketBase a MinIO.
- **Modelo ML**: Archivo `diabcare-app/modelos/modelo_diabetes.pkl` en MinIO con el modelo RandomForest entrenado.

---

## Requisitos Funcionales

### Requisito 1: Autenticación y Sesión

**User Story:** Como usuario, quiero iniciar sesión con email y contraseña para acceder al sistema con mi rol asignado.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `POST /api/auth/login` que valide credenciales y retorne un token JWT con `sub`, `email`, `rol` y `exp`.
2. WHEN las credenciales son correctas, THE Sistema SHALL retornar HTTP 200 con `token`, `tipo` y `usuario` (id, nombre, email, rol).
3. IF las credenciales son incorrectas, THE Sistema SHALL retornar HTTP 401 con `detail: "Credenciales incorrectas"`.
4. THE Sistema SHALL tener un usuario administrador por defecto: `admin@diabcare.com` / `Admin2026*`.
5. THE Frontend SHALL almacenar el token en `localStorage` y redirigir al Dashboard tras login exitoso.
6. WHEN el token expira o es inválido, THE Sistema SHALL retornar HTTP 401 y THE Frontend SHALL redirigir al login.
7. THE Sistema SHALL exponer `POST /api/auth/logout` que retorne confirmación de cierre de sesión.
8. THE Sistema SHALL exponer `PUT /api/auth/cambiar-password` con validación de password actual.
9. THE Sistema SHALL exponer `POST /api/auth/recuperar` y `POST /api/auth/resetear` para reset de password vía código.

---

### Requisito 2: Gestión de Usuarios

**User Story:** Como administrador, quiero gestionar usuarios del sistema para controlar quién accede y con qué rol.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/usuarios/` que retorne lista de usuarios con id, nombre, email, rol, activo, creado_en (sin password_hash).
2. THE Sistema SHALL exponer `POST /api/usuarios/` para crear usuarios con nombre, email, password y rol.
3. IF el email ya existe, THE Sistema SHALL retornar HTTP 400 con `detail: "Email ya registrado"`.
4. THE Sistema SHALL exponer `PUT /api/usuarios/{id}/rol` para cambiar el rol de un usuario.
5. THE Sistema SHALL exponer `DELETE /api/usuarios/{id}` que desactiva el usuario (activo=False) sin eliminarlo.
6. THE Sistema SHALL almacenar usuarios en formato Parquet en MinIO (`diabcare-app/usuarios/usuarios.parquet`).
7. THE Sistema SHALL encriptar contraseñas con SHA-256 antes de almacenarlas.
8. THE Frontend SHALL mostrar KPI cards con total, activos, inactivos y administradores.
9. THE Frontend SHALL permitir búsqueda en tiempo real por nombre o email.
10. THE Frontend SHALL mostrar avatares con inicial del nombre y colores por índice.
11. THE Frontend SHALL restringir la página de usuarios solo al rol administrador mediante `aplicarRoles()`.

---

### Requisito 3: Dataset y Generación de Datos

**User Story:** Como analista, quiero explorar el dataset clínico y generar datos sintéticos para poblar MinIO.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/dataset/hechos` con paginación (`skip`, `limit`) que retorne el total real de registros usando `pyarrow.parquet.ParquetFile.metadata.num_rows` y los datos del parquet más reciente.
2. THE Sistema SHALL exponer `GET /api/dataset/dimension/{nombre}` para las dimensiones: `paciente`, `ubicacion`, `raza`, `condicion`.
3. THE Sistema SHALL exponer `GET /api/dataset/estadisticas` que retorne total, con_diabetes, sin_diabetes y columnas usando pyarrow para conteo rápido sin cargar todo el dataset en memoria.
4. THE Sistema SHALL exponer `POST /api/dataset/generar` que genere `cantidad` registros sintéticos y los suba a MinIO en formato Parquet.
5. WHEN la generación es exitosa, THE Sistema SHALL retornar `mensaje`, `archivo` (ruta en MinIO) y `total` (registros generados).
6. THE Sistema SHALL generar registros con campos en español: year, gender (Masculino/Femenino/Otro), age, location (ciudades en español), razas (flags 0/1), hypertension, heart_disease, smoking_history (nunca/actual/no actual/Sin información), bmi, hbA1c_level, blood_glucose_level, diabetes.
7. THE Frontend SHALL mostrar presets de cantidad (1K, 10K, 50K, 100K, 500K).
8. THE Frontend SHALL mostrar barra de progreso animada con pasos: Generando → Parquet → MinIO → Completado.
9. THE Frontend SHALL mostrar card de resultado con registros generados, año y nombre del archivo.
10. THE Frontend (ver tablas) SHALL mostrar el total real de registros de todos los parquets concatenados.

---

### Requisito 4: Registros Clínicos

**User Story:** Como médico, quiero consultar y filtrar registros clínicos del dataset para análisis específicos.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/registros/` con paginación y retornar `total` y `registros`.
2. THE Sistema SHALL exponer `GET /api/registros/buscar` con filtros opcionales: `diabetes`, `gender`, `location`, `age_min`, `age_max`.
3. THE Sistema SHALL exponer `POST /api/registros/` para crear nuevos registros clínicos.
4. THE Sistema SHALL exponer `PUT /api/registros/{id}` para actualizar campos clínicos.
5. THE Sistema SHALL exponer `DELETE /api/registros/{id}` para eliminar un registro.
6. THE Frontend SHALL mostrar tabla paginada con navegación anterior/siguiente.
7. THE Frontend SHALL permitir filtros por diabetes, género, ubicación y rango de edad.
8. NOTA: La ruta `/estadisticas` DEBE declararse ANTES de `/{encounter_id}` en el router FastAPI para evitar colisión de paths.

---

### Requisito 5: Estadísticas Clínicas

**User Story:** Como analista, quiero ver estadísticas detalladas del dataset para identificar patrones clínicos.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/registros/estadisticas` que retorne datos reales calculados desde el DataFrame concatenado de todos los parquets en `stage/`.
2. THE endpoint SHALL retornar: total, con_diabetes, sin_diabetes, genero, tabaquismo, razas, edad (rangos pd.cut), promedios (bmi/hba1c/glucosa con/sin diabetes), comorbilidades, ubicaciones (top 10), tendencia (por año).
3. THE Frontend SHALL mostrar KPI cards con total, con_diabetes, sin_diabetes, prevalencia.
4. THE Frontend SHALL mostrar 10+ gráficas Chart.js: donut, género, comorbilidades, edad, raza, tabaquismo, top ubicaciones, tendencia por año.
5. THE Frontend SHALL mostrar barras comparativas inline de promedios clínicos.

---

### Requisito 6: Dashboard Ejecutivo

**User Story:** Como usuario, quiero ver un resumen ejecutivo del sistema al ingresar.

#### Criterios de Aceptación

1. THE Dashboard SHALL consumir `GET /api/registros/estadisticas` y `GET /api/dataset/estadisticas`.
2. THE Dashboard SHALL mostrar 4 KPI cards: total registros, con diabetes, sin diabetes, prevalencia.
3. THE Dashboard SHALL mostrar donut compacto de distribución diabetes con porcentajes.
4. THE Dashboard SHALL mostrar 4 accesos rápidos a: Estadísticas, Registros, Dataset, Generador.
5. THE Dashboard SHALL generar alertas clínicas dinámicas: prevalencia > 50% → alerta roja, HbA1c > 7.5 → alerta roja, volumen < 1000 → alerta azul.
6. THE Dashboard SHALL mostrar promedios clínicos con/sin diabetes con badges de color.
7. THE Dashboard SHALL mostrar top 6 ubicaciones con barras proporcionales.
8. THE Dashboard SHALL mostrar estado del sistema: MinIO, Dataset, API Backend, Autenticación, Modelo ML, Pipeline.
9. THE Dashboard SHALL mostrar últimos archivos en MinIO con columnas del dataset.

---

### Requisito 7: Predicción ML

**User Story:** Como médico, quiero predecir si un paciente tiene diabetes ingresando sus datos clínicos.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `POST /api/prediccion/entrenar` que entrene un modelo RandomForest (100 árboles) con el dataset completo concatenado desde MinIO, con split 80/20 estratificado.
2. WHEN el entrenamiento termina, THE Sistema SHALL guardar el modelo serializado con pickle en MinIO `diabcare-app/modelos/modelo_diabetes.pkl` junto con las métricas calculadas.
3. THE Sistema SHALL exponer `POST /api/prediccion/` que reciba `age`, `bmi`, `hbA1c_level`, `blood_glucose_level`, `hypertension`, `heart_disease` y retorne `diagnostico` (0/1), `resultado` (texto), `probabilidad` (float) y `riesgo` (Alto/Medio/Bajo).
4. THE Sistema SHALL exponer `GET /api/prediccion/metricas` que retorne accuracy, precision, recall, f1, registros_entrenamiento, registros_prueba.
5. THE Sistema SHALL exponer `GET /api/prediccion/estado` que indique si el modelo está disponible en MinIO.
6. THE Sistema SHALL cachear el modelo en memoria (`_modelo_cache`) para evitar descargarlo en cada predicción.
7. THE Frontend SHALL mostrar 4 metric cards: Accuracy, Precision, Recall, F1-Score.
8. THE Frontend SHALL mostrar formulario con 6 campos clínicos y botón de predicción.
9. THE Frontend SHALL mostrar resultado con diagnóstico, barra de probabilidad animada y badge de riesgo (Alto/Medio/Bajo).
10. THE Frontend SHALL mostrar referencia clínica: HbA1c > 6.5% indica diabetes, Glucosa > 200 mg/dL indica diabetes, BMI > 30 factor de riesgo.
11. THE Frontend SHALL aplicar `aplicarRoles()` dentro de la función de predicción para evitar flash del sidebar incorrecto.

---

### Requisito 8: Pipeline ETL

**User Story:** Como administrador, quiero ver y ejecutar el pipeline ELT para verificar el flujo de datos.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/pipeline/estado` que liste los archivos Parquet en MinIO `stage/` con nombre, ruta, tamaño en MB y fecha de modificación, ordenados por fecha descendente.
2. THE endpoint SHALL retornar: estado, bucket, prefix, total_archivos, ultimo_archivo, ultima_fecha, archivos (top 10).
3. THE Frontend SHALL mostrar flujo visual con 5 nodos: PocketBase → Airflow → MinIO → Parquet → FastAPI.
4. THE Frontend SHALL mostrar 4 KPI cards: Estado MinIO, Archivos Parquet, Último archivo, Última carga.
5. THE Frontend SHALL mostrar lista de archivos Parquet con nombre, tamaño MB y fecha.
6. THE Frontend SHALL mostrar los 4 pasos del pipeline ELT con descripción y comando técnico.
7. THE Frontend SHALL tener botón "Ejecutar pipeline" que simule visualmente los 4 pasos en secuencia: Extracción (⏳ running → ✓ done), Transformación, Carga MinIO (verifica via `/api/pipeline/estado`), Consumo FastAPI (verifica via `/api/registros/estadisticas`).
8. WHEN un paso está ejecutando, THE Frontend SHALL mostrar animación pulse en el número del paso.
9. WHEN un paso completa, THE Frontend SHALL mostrar el número en verde con ✓.

---

## Requisitos No Funcionales

### RNF-01: Seguridad
1. Todos los endpoints (excepto `/api/auth/login` y páginas frontend) SHALL requerir token JWT válido.
2. Los roles SHALL restringir acceso: `usuarios/configuracion/auditoria` → solo administrador; `registros/analisis/prediccion/reportes` → administrador y médico; `dataset/pipeline_etl/modelo_ml/integraciones` → administrador y analista; `notificaciones` → todos los roles.
3. Las contraseñas SHALL almacenarse como hash SHA-256, nunca en texto plano.
4. El sidebar SHALL ocultar los grupos de navegación no permitidos para el rol mediante la función `aplicarRoles()` en cada página, usando `setTimeout(aplicarRoles, 50)` para evitar flash visual.

### RNF-02: Rendimiento
1. Conteo de registros totales SHALL usar `pyarrow.parquet.ParquetFile.metadata.num_rows` para leer solo el footer sin deserializar datos — resultado en < 2 segundos para 10 archivos Parquet.
2. Endpoints de estadísticas SHALL responder en menos de 10 segundos con 600k+ registros.
3. El modelo ML SHALL cachearse en memoria tras la primera carga para evitar descarga repetida desde MinIO.

### RNF-03: Usabilidad
1. THE Frontend SHALL aplicar tema oscuro consistente con variables CSS compartidas en `estilos.css`.
2. THE Frontend SHALL mostrar spinners durante operaciones de red.
3. THE Frontend SHALL mostrar toasts de confirmación/error (verde/rojo) con auto-dismiss a los 3 segundos.
4. THE Sidebar SHALL ser consistente en todas las páginas con el mismo HTML de navegación.

### RNF-04: Disponibilidad
1. THE Sistema SHALL inicializar buckets MinIO (`diabetes-data`, `diabcare-app`) automáticamente al arrancar si no existen.
2. THE Sistema SHALL crear el usuario admin por defecto si el Parquet de usuarios está vacío.
3. `warnings.filterwarnings("ignore", category=UserWarning)` SHALL suprimir logs de JWT key length.
4. `GET /favicon.ico` SHALL retornar HTTP 204 para suprimir logs de 404 en consola.
