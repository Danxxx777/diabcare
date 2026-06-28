# Requirements Document

## Introduction

DiabCare Analytics es una plataforma SaaS académica (6to semestre — Construcción del Software) para la gestión y análisis de datos clínicos de diabetes hospitalaria. El sistema lee archivos `.parquet` almacenados en MinIO, genera estadísticas clínicas con pandas, expone visualizaciones analíticas, gestión de usuarios, registros clínicos, predicción ML y pipeline ELT con autenticación JWT por roles.

**Stack tecnológico:** FastAPI + Python 3.14 (backend), MinIO (object storage), pandas (transformación ELT), scikit-learn (ML), pyarrow (lectura eficiente de Parquet), HTML/CSS/JS vanilla (frontend multi-página), PocketBase (fuente origen), Apache Airflow 2.9.1 Docker (orquestación), Uvicorn (servidor).

---

## Glossary

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

## Requirements

### Requirement 1: Autenticación y Sesión

**User Story:** Como usuario, quiero iniciar sesión con email y contraseña para acceder al sistema con mi rol asignado.

#### Acceptance Criteria

1. THE Sistema SHALL exponer `POST /api/auth/login` que valide credenciales y retorne un token JWT con `sub`, `email`, `rol` y `exp` con expiración de 8 horas.
2. WHEN las credenciales son correctas, THE Sistema SHALL retornar HTTP 200 con `token` (string JWT), `tipo` (string "bearer") y `usuario` (objeto con id, nombre, email, rol).
3. IF las credenciales son incorrectas o el usuario no existe, THE Sistema SHALL retornar HTTP 401 con `detail: "Credenciales incorrectas"` sin distinguir cuál campo es incorrecto.
4. IF el usuario existe pero tiene `activo=False`, THE Sistema SHALL retornar HTTP 401 con `detail: "Credenciales incorrectas"` (sin revelar que la cuenta está desactivada).
5. THE Sistema SHALL garantizar que existe al menos un usuario administrador por defecto con email `admin@diabcare.com` al arrancar si no hay usuarios en el sistema.
6. WHEN el login es exitoso, THE Frontend SHALL almacenar el token JWT en `localStorage` bajo la clave `token` y el objeto usuario bajo la clave `usuario`, luego redirigir a `/paginas/analisis/index.html`.
7. WHEN el token expira o su firma es inválida, THE Sistema SHALL retornar HTTP 401 en cualquier endpoint protegido, y THE Frontend SHALL eliminar `token` y `usuario` de `localStorage` y redirigir a `/paginas/autenticacion/index.html`.
8. THE Sistema SHALL exponer `POST /api/auth/logout` que retorne HTTP 200 con `{"mensaje": "Sesión cerrada"}`.
9. THE Sistema SHALL exponer `PUT /api/auth/cambiar-password` que valide el password actual antes de actualizar el hash SHA-256 en MinIO; IF el password actual no coincide, SHALL retornar HTTP 400.
10. THE Sistema SHALL exponer `POST /api/auth/recuperar` que acepte `{"email": string}` y retorne HTTP 200 independientemente de si el email existe, para no revelar la existencia de cuentas.
11. THE Sistema SHALL exponer `POST /api/auth/resetear` que acepte un código de reset válido y un nuevo password; IF el código es inválido o expirado, SHALL retornar HTTP 400.

---

### Requirement 2: Gestión de Usuarios

**User Story:** Como administrador, quiero gestionar usuarios del sistema para controlar quién accede y con qué rol.

#### Acceptance Criteria

1. WHEN un usuario con rol `administrador` realiza `GET /api/usuarios/`, THE Sistema SHALL retornar HTTP 200 con lista de usuarios conteniendo id, nombre, email, rol, activo, creado_en por cada usuario, sin incluir el campo `password_hash`.
2. WHEN un administrador realiza `POST /api/usuarios/` con nombre, email, password y rol válidos, THE Sistema SHALL crear el usuario con `activo=True`, `creado_en` en formato ISO 8601, y password almacenado como hash SHA-256, retornando HTTP 201.
3. IF el email proporcionado en `POST /api/usuarios/` ya existe en el sistema (activo o inactivo), THE Sistema SHALL retornar HTTP 400 con `detail: "Email ya registrado"`.
4. IF el rol proporcionado en `POST /api/usuarios/` o `PUT /api/usuarios/{id}/rol` no es uno de `administrador`, `medico`, `analista`, THE Sistema SHALL retornar HTTP 400 con `detail: "Rol inválido"`.
5. WHEN un administrador realiza `PUT /api/usuarios/{id}/rol` con un rol válido, THE Sistema SHALL actualizar el rol del usuario y retornar HTTP 200 con el usuario actualizado.
6. IF el `id` en `PUT /api/usuarios/{id}/rol` o `DELETE /api/usuarios/{id}` no corresponde a ningún usuario, THE Sistema SHALL retornar HTTP 404 con `detail: "Usuario no encontrado"`.
7. WHEN un administrador realiza `DELETE /api/usuarios/{id}`, THE Sistema SHALL establecer `activo=False` en el registro del usuario sin eliminarlo del Parquet, retornando HTTP 200.
8. IF un administrador intenta desactivarse a sí mismo o cambiar su propio rol, THE Sistema SHALL retornar HTTP 400 con `detail: "No puede modificar su propia cuenta"`.
9. THE Sistema SHALL persistir todos los cambios de usuarios en formato Parquet en MinIO en la ruta `diabcare-app/usuarios/usuarios.parquet`, sobrescribiendo el archivo completo tras cada modificación.
10. THE Frontend SHALL mostrar 4 KPI cards con los conteos de: total de usuarios, usuarios activos, usuarios inactivos y usuarios con rol administrador.
11. WHEN el usuario escribe en el campo de búsqueda, THE Frontend SHALL filtrar la lista de usuarios en tiempo real (máximo 300ms de latencia) mostrando solo los que coincidan con nombre o email (búsqueda case-insensitive).
12. THE Frontend SHALL mostrar un avatar circular para cada usuario con la inicial en mayúscula de su nombre y un color de fondo determinado por `índice % colores.length`.
13. WHEN un usuario sin rol `administrador` intenta acceder a `/paginas/usuarios/index.html`, THE Frontend SHALL redirigir a `/paginas/analisis/index.html` al ejecutarse `aplicarRoles()`.

---

### Requirement 3: Dataset y Generación de Datos

**User Story:** Como analista, quiero explorar el dataset clínico y generar datos sintéticos para poblar MinIO.

#### Acceptance Criteria

1. WHEN se realiza `GET /api/dataset/hechos` con parámetros `skip` (entero ≥ 0, default 0) y `limit` (entero 1–1000, default 100), THE Sistema SHALL retornar HTTP 200 con `total` (suma de `num_rows` de todos los Parquet en `stage/` via pyarrow footer) y `registros` (filas del Parquet más reciente en el rango solicitado). IF no hay archivos en `stage/`, SHALL retornar `{"total": 0, "registros": []}`.
2. WHEN se realiza `GET /api/dataset/dimension/{nombre}` con `nombre` en `["paciente", "ubicacion", "raza", "condicion"]`, THE Sistema SHALL retornar HTTP 200 con los valores únicos de esa dimensión. IF `nombre` no está en la lista permitida, SHALL retornar HTTP 404 con `detail: "Dimensión no encontrada"`.
3. WHEN se realiza `GET /api/dataset/estadisticas`, THE Sistema SHALL retornar HTTP 200 con `total`, `con_diabetes`, `sin_diabetes` y `columnas`, calculando `total` usando `pyarrow.parquet.ParquetFile.metadata.num_rows` sin cargar los datos en memoria. IF no hay archivos Parquet, SHALL retornar `{"total": 0, "con_diabetes": 0, "sin_diabetes": 0, "columnas": []}`.
4. WHEN se realiza `POST /api/dataset/generar` con `cantidad` (entero 1–500000) y `year` (entero 2010–2030), THE Sistema SHALL generar exactamente `cantidad` registros sintéticos y subirlos a MinIO `diabetes-data/stage/` en formato Parquet con nombre `datos_{year}_{timestamp}.parquet`.
5. IF `cantidad` está fuera del rango [1, 500000] o `year` está fuera del rango [2010, 2030], THE Sistema SHALL retornar HTTP 422 con detalle de los campos inválidos.
6. WHEN la generación es exitosa, THE Sistema SHALL retornar HTTP 200 con `mensaje` (string), `archivo` (ruta completa en MinIO incluyendo bucket y prefijo) y `total` (entero igual a `cantidad` solicitada).
7. THE Sistema SHALL generar cada registro con los siguientes campos y rangos: `year` (igual al parámetro), `gender` (uno de: "Masculino", "Femenino", "Otro"), `age` (float 1.0–80.0), `location` (string de ciudad en español), exactamente una de las flags de raza en 1 (`race_AfricanAmerican`, `race_Asian`, `race_Caucasian`, `race_Hispanic`, `race_Other`), `hypertension` (0/1), `heart_disease` (0/1), `smoking_history` (uno de: "nunca", "actual", "no actual", "Sin información"), `bmi` (float 15.0–45.0), `hbA1c_level` (float 3.5–9.0), `blood_glucose_level` (entero 80–300), `diabetes` (0/1).
8. WHEN se carga la página del generador, THE Frontend SHALL mostrar 5 botones de preset con los valores 1000, 10000, 50000, 100000 y 500000 que al hacer clic completen automáticamente el campo `cantidad`.
9. WHILE la generación está en progreso, THE Frontend SHALL mostrar una barra de progreso animada avanzando secuencialmente por los pasos: "Generando registros", "Convirtiendo a Parquet", "Subiendo a MinIO", "Completado".
10. WHEN la generación completa exitosamente, THE Frontend SHALL mostrar una card de resultado con: número de registros generados, el año de los datos y el nombre del archivo subido a MinIO.
11. WHEN se carga la página de ver tablas, THE Frontend SHALL obtener `total` desde `GET /api/dataset/hechos` o `GET /api/dataset/estadisticas` y mostrarlo como el total real de registros concatenados de todos los Parquets en `stage/`.

---

### Requirement 4: Registros Clínicos

**User Story:** Como médico, quiero consultar y filtrar registros clínicos del dataset para análisis específicos.

#### Acceptance Criteria

1. WHEN se realiza `GET /api/registros/` con parámetros opcionales `limit` (entero 1–500, default 50) y `offset` (entero ≥ 0, default 0), THE Sistema SHALL retornar HTTP 200 con `total` (conteo total sin paginación) y `registros` (lista de registros en el rango solicitado).
2. WHEN se realiza `GET /api/registros/buscar` con filtros opcionales `diabetes` (0/1), `gender` (string), `location` (string), `age_min` (float 0–120), `age_max` (float 0–120), THE Sistema SHALL retornar HTTP 200 con hasta 100 registros que satisfagan todos los filtros activos simultáneamente. IF `age_min > age_max`, SHALL retornar HTTP 422.
3. WHEN se realiza `POST /api/registros/` con todos los campos clínicos requeridos, THE Sistema SHALL crear el registro y retornar HTTP 201 con el registro creado incluyendo su `encounter_id` generado. IF faltan campos requeridos, SHALL retornar HTTP 422 con detalle de los campos faltantes.
4. WHEN se realiza `PUT /api/registros/{encounter_id}` con campos clínicos válidos, THE Sistema SHALL actualizar el registro y retornar HTTP 200 con el registro actualizado. IF el `encounter_id` no existe, SHALL retornar HTTP 404 con `detail: "Registro no encontrado"`.
5. WHEN se realiza `DELETE /api/registros/{encounter_id}`, THE Sistema SHALL eliminar el registro y retornar HTTP 200 con confirmación. IF el `encounter_id` no existe, SHALL retornar HTTP 404 con `detail: "Registro no encontrado"`.
6. WHEN se realiza `GET /api/registros/{encounter_id}`, THE Sistema SHALL retornar HTTP 200 con el registro individual. IF el `encounter_id` no existe, SHALL retornar HTTP 404 con `detail: "Registro no encontrado"`.
7. THE Frontend SHALL mostrar los registros en una tabla paginada con botones de navegación "Anterior" y "Siguiente", deshabilitando "Anterior" en la primera página y "Siguiente" en la última.
8. THE Frontend SHALL permitir al usuario filtrar la tabla por: estado de diabetes (desplegable: Todos/Con diabetes/Sin diabetes), género, ubicación y rango de edad (edad mínima y máxima), aplicando todos los filtros seleccionados simultáneamente.
9. THE Sistema SHALL declarar la ruta `GET /api/registros/estadisticas` antes de `GET /api/registros/{encounter_id}` en el router FastAPI para evitar que `"estadisticas"` sea interpretado como un `encounter_id`.

---

### Requirement 5: Estadísticas Clínicas

**User Story:** Como analista, quiero ver estadísticas detalladas del dataset para identificar patrones clínicos.

#### Acceptance Criteria

1. WHEN se realiza `GET /api/registros/estadisticas`, THE Sistema SHALL retornar HTTP 200 con datos calculados desde el DataFrame resultante de concatenar todos los Parquets en `diabetes-data/stage/` cargados en memoria con pandas. IF no hay archivos Parquet disponibles en MinIO, THE Sistema SHALL retornar HTTP 200 con todos los campos numéricos en 0 y las listas vacías.
2. THE endpoint SHALL retornar un objeto JSON con los campos: `total` (entero), `con_diabetes` (entero), `sin_diabetes` (entero), `prevalencia` (float, porcentaje redondeado a 2 decimales = con_diabetes/total*100), `genero` (dict de conteos por valor de `gender`), `tabaquismo` (dict de conteos por `smoking_history` cruzado con `diabetes`), `razas` (dict de sumas de cada flag `race_*` separadas por grupo diabetes), `edad` (dict de conteos por rangos: <20, 20-30, 31-40, 41-50, 51-60, 61-70, >70), `promedios` (objeto con `bmi`, `hbA1c_level`, `blood_glucose_level` cada uno con `con_diabetes` y `sin_diabetes` redondeados a 2 decimales), `comorbilidades` (dict cruzando `hypertension`/`heart_disease` con `diabetes`), `ubicaciones` (lista de las 10 ubicaciones con mayor conteo con nombre y conteo), `tendencia` (lista de objetos por año con `year`, `total` y `con_diabetes`).
3. THE Frontend SHALL mostrar 4 KPI cards con los valores: total de registros, cantidad con diabetes, cantidad sin diabetes, y prevalencia (porcentaje con 2 decimales y símbolo %).
4. THE Frontend SHALL mostrar al menos las siguientes gráficas Chart.js: donut de distribución diabetes, barras de distribución por género, barras de comorbilidades, barras de distribución por rango de edad, barras de distribución por raza, barras de historial de tabaquismo, barras horizontales del top 10 de ubicaciones, línea de tendencia por año.
5. THE Frontend SHALL mostrar barras comparativas de promedios clínicos (bmi, HbA1c, glucosa) mostrando el valor con diabetes vs. sin diabetes en la misma barra con colores diferenciados.

---

### Requirement 6: Dashboard Ejecutivo

**User Story:** Como usuario, quiero ver un resumen ejecutivo del sistema al ingresar.

#### Acceptance Criteria

1. WHEN se carga el Dashboard, THE Frontend SHALL realizar llamadas a `GET /api/registros/estadisticas` y `GET /api/dataset/estadisticas` en paralelo y poblar los componentes con los datos recibidos.
2. IF alguna de las llamadas a la API falla o excede 15 segundos, THE Frontend SHALL mostrar un estado de error en los componentes afectados con el mensaje "Error al cargar datos" sin bloquear los componentes que sí respondieron.
3. THE Dashboard SHALL mostrar 4 KPI cards con los valores: total de registros, cantidad con diabetes, cantidad sin diabetes, y prevalencia (float redondeado a 2 decimales con símbolo %).
4. THE Dashboard SHALL mostrar un gráfico donut de distribución diabetes con los porcentajes de con_diabetes y sin_diabetes como etiquetas.
5. THE Dashboard SHALL mostrar 4 tarjetas de acceso rápido con enlaces a: `/paginas/estadisticas/index.html`, `/paginas/registros_clinicos/index.html`, `/paginas/dataset/index.html`, `/paginas/dataset/generador.html`.
6. IF la prevalencia supera el 50%, THE Dashboard SHALL mostrar una alerta con estilo visual rojo con el texto indicando el porcentaje de prevalencia.
7. IF el valor promedio de `hbA1c_level` con diabetes supera 7.5, THE Dashboard SHALL mostrar una alerta con estilo visual rojo indicando el valor de HbA1c.
8. IF el `total` de registros es menor a 1000, THE Dashboard SHALL mostrar una alerta con estilo visual azul indicando el bajo volumen de datos.
9. THE Dashboard SHALL mostrar promedios clínicos (bmi, HbA1c, glucosa) para el grupo con diabetes y sin diabetes, con badge verde si el valor con diabetes es mayor que sin diabetes y badge rojo en caso contrario.
10. THE Dashboard SHALL mostrar las top 6 ubicaciones con mayor cantidad de registros con barras proporcionales cuyo ancho máximo representa la ubicación con más registros.
11. THE Dashboard SHALL mostrar el estado de cada componente del sistema: MinIO, Dataset, API Backend, Autenticación, Modelo ML, Pipeline; mostrando "Operacional" si el componente responde correctamente o "No disponible" si no responde.
12. THE Dashboard SHALL mostrar los últimos 5 archivos Parquet en MinIO con nombre de archivo y columnas del dataset obtenidos desde `GET /api/pipeline/estado`.

---

### Requirement 7: Predicción ML

**User Story:** Como médico, quiero predecir si un paciente tiene diabetes ingresando sus datos clínicos.

#### Acceptance Criteria

1. WHEN se realiza `POST /api/prediccion/entrenar`, THE Sistema SHALL cargar el DataFrame completo desde todos los Parquets en `diabetes-data/stage/`, entrenar un `RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)` con split estratificado 80/20, y retornar HTTP 200 con las métricas calculadas. IF no hay datos disponibles, SHALL retornar HTTP 400 con `detail: "No hay datos disponibles para entrenar"`.
2. WHEN el entrenamiento termina exitosamente, THE Sistema SHALL serializar el modelo y las métricas con pickle en un dict `{"modelo": ..., "metricas": ...}` y subirlo a MinIO en `diabcare-app/modelos/modelo_diabetes.pkl`, sobreescribiendo versiones anteriores.
3. WHEN se realiza `POST /api/prediccion/` con campos válidos `age` (float 1–120), `bmi` (float 10–60), `hbA1c_level` (float 3–15), `blood_glucose_level` (float 50–500), `hypertension` (0/1), `heart_disease` (0/1), THE Sistema SHALL retornar HTTP 200 con `diagnostico` (0/1), `resultado` (string "Con diabetes" o "Sin diabetes"), `probabilidad` (float 0.0–1.0 redondeado a 4 decimales) y `riesgo` (string: "Alto" si probabilidad ≥ 0.7, "Medio" si ≥ 0.4, "Bajo" si < 0.4).
4. IF se realiza `POST /api/prediccion/` y el modelo no está disponible en MinIO ni en caché, THE Sistema SHALL retornar HTTP 400 con `detail: "Modelo no disponible. Entrena el modelo primero en POST /api/prediccion/entrenar"`.
5. IF algún campo de `POST /api/prediccion/` está fuera de sus rangos válidos, THE Sistema SHALL retornar HTTP 422 con detalle de los campos inválidos.
6. THE Sistema SHALL exponer `GET /api/prediccion/metricas` que retorne HTTP 200 con `accuracy`, `precision`, `recall`, `f1` (todos float 0.0–1.0), `registros_entrenamiento` (int) y `registros_prueba` (int). IF el modelo no está disponible, SHALL retornar HTTP 400 con `detail: "Modelo no disponible"`.
7. THE Sistema SHALL exponer `GET /api/prediccion/estado` que retorne HTTP 200 con `{"disponible": true}` si el archivo `diabcare-app/modelos/modelo_diabetes.pkl` existe en MinIO, o `{"disponible": false}` si no existe.
8. THE Sistema SHALL mantener el modelo en caché en memoria tras la primera carga exitosa desde MinIO para evitar re-descargas en predicciones subsecuentes, invalidando la caché al completar un nuevo entrenamiento.
9. THE Frontend SHALL mostrar 4 metric cards con los valores de Accuracy, Precision, Recall y F1-Score obtenidos de `GET /api/prediccion/metricas`, formateados como porcentaje con 1 decimal.
10. THE Frontend SHALL mostrar un formulario con 6 campos: Edad, BMI, HbA1c, Glucosa en sangre, Hipertensión (checkbox), Cardiopatía (checkbox), y un botón "Predecir".
11. WHEN la predicción retorna resultado, THE Frontend SHALL mostrar: diagnóstico textual ("Con diabetes" / "Sin diabetes"), barra de progreso animada mostrando el valor de probabilidad de 0 a 100%, y un badge de riesgo ("Alto" en rojo, "Medio" en ámbar, "Bajo" en verde).
12. THE Frontend SHALL mostrar una sección de referencia clínica estática con: HbA1c > 6.5% indica diabetes, Glucosa > 200 mg/dL indica diabetes, BMI > 30 es factor de riesgo.
13. THE Frontend SHALL llamar a `aplicarRoles()` dentro de la función de predicción tras actualizar el DOM para evitar que el sidebar muestre ítems no autorizados después de la re-renderización.

---

### Requirement 8: Pipeline ETL

**User Story:** Como administrador, quiero ver y ejecutar el pipeline ELT para verificar el flujo de datos.

#### Acceptance Criteria

1. WHEN se realiza `GET /api/pipeline/estado`, THE Sistema SHALL conectarse a MinIO y listar los archivos Parquet en `diabetes-data/stage/`, retornando HTTP 200 con los campos: `estado` ("activo" si MinIO responde, "inactivo" si no), `bucket` ("diabetes-data"), `prefix` ("stage/"), `total_archivos` (entero), `ultimo_archivo` (nombre del archivo más reciente o null), `ultima_fecha` (fecha ISO 8601 del archivo más reciente o null), `archivos` (lista de los 10 archivos más recientes con nombre, ruta, tamaño_mb redondeado a 2 decimales y fecha_modificacion en ISO 8601). IF MinIO no es accesible, SHALL retornar HTTP 200 con `estado: "inactivo"` y listas vacías.
2. THE Frontend SHALL mostrar un flujo visual con exactamente 5 nodos en secuencia: "PocketBase" → "Airflow" → "MinIO" → "Parquet" → "FastAPI", con líneas de conexión entre nodos adyacentes.
3. THE Frontend SHALL mostrar 4 KPI cards con: estado de MinIO ("Operacional" / "No disponible"), cantidad de archivos Parquet en `stage/`, nombre del último archivo subido, y fecha de la última carga en formato legible.
4. THE Frontend SHALL mostrar la lista de archivos Parquet retornada por el endpoint con columnas: nombre del archivo, tamaño en MB y fecha de modificación.
5. THE Frontend SHALL mostrar los 4 pasos del pipeline ETL numerados (1–4) con descripción textual y el comando técnico asociado a cada paso.
6. WHEN el usuario hace clic en "Ejecutar pipeline", THE Frontend SHALL ejecutar los 4 pasos en secuencia, mostrando animación pulse (CSS `animation: pulse`) en el número del paso activo.
7. WHEN cada paso completa, THE Frontend SHALL cambiar el número del paso a color verde (#22c55e) con símbolo ✓, y avanzar al siguiente paso. Los pasos 3 y 4 verifican el estado real llamando a `GET /api/pipeline/estado` y `GET /api/registros/estadisticas` respectivamente, completando exitosamente si reciben HTTP 200.
8. IF cualquier paso del pipeline falla (recibe HTTP distinto de 200 o timeout > 30 segundos), THE Frontend SHALL mostrar el número del paso en rojo con símbolo ✗ y detener la secuencia mostrando un mensaje de error con el paso que falló.

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
