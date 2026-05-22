# Documento de Requisitos — DiabCare Analytics

## Introducción

DiabCare Analytics es una aplicación web académica (6to semestre — Construcción del Software) para la gestión y análisis de datos clínicos de diabetes hospitalaria. El sistema lee un archivo `.parquet` almacenado en MinIO, genera tablas de hecho y dimensiones en memoria con pandas, y expone visualizaciones analíticas, consultas de tablas y la información corporativa de la empresa ficticia DiabCare Analytics.

El stack tecnológico es: FastAPI + Python (backend), MinIO como object storage (fuente de datos), pandas (transformación en memoria), Jinja2 + HTML/JS vanilla (frontend), Uvicorn (servidor).

---

## Glosario

- **Sistema**: La aplicación web DiabCare Analytics en su conjunto (backend FastAPI + frontend HTML/JS).
- **API**: El conjunto de endpoints REST expuestos por el backend FastAPI.
- **Parquet_MinIO**: El archivo `.parquet` más reciente almacenado en el bucket `diabetes-data`, prefijo `stage/`, en el servidor MinIO local.
- **Dataset**: El DataFrame de pandas cargado en memoria a partir del Parquet_MinIO, con ~100,000 registros del dataset clínico de diabetes.
- **Cache_DF**: La variable global `_df_cache` en `main.py` que almacena el DataFrame en memoria tras la primera carga desde MinIO.
- **Tabla_Virtual**: Cada una de las 6 vistas tabulares generadas en memoria por pandas a partir del Dataset: `diabetes_dataset`, `dim_paciente`, `dim_ubicacion`, `dim_raza`, `dim_condicion`, `fact_diabetes`.
- **dim_paciente**: Dimensión de pacientes con columnas `id_paciente`, `gender`, `age`.
- **dim_ubicacion**: Dimensión de ubicaciones con columnas `id_ubicacion`, `location`, `year`.
- **dim_raza**: Dimensión de razas con columnas `id_raza` y las columnas de raza del dataset (`race_AfricanAmerican`, `race_Asian`, `race_Caucasian`, `race_Hispanic`, `race_Other`).
- **dim_condicion**: Dimensión de condiciones preexistentes con columnas `id_condicion`, `hypertension`, `heart_disease`, `smoking_history`.
- **fact_diabetes**: Tabla de hechos con columnas `id_fact`, `bmi`, `hbA1c_level`, `blood_glucose_level`, `diabetes`.
- **TABLAS_MAP**: El diccionario Python en `main.py` que mapea nombres de tabla a funciones generadoras de DataFrames. Define la whitelist de tablas accesibles.
- **Dashboard**: La sección principal del frontend que muestra tarjetas de estadísticas del Dataset y las Tablas_Virtuales.
- **Frontend**: La interfaz de usuario SPA servida como plantilla Jinja2 (`index.html`).
- **Usuario**: Persona que interactúa con el Frontend a través de un navegador web.
- **Pipeline_Externo**: El flujo externo al Sistema compuesto por PocketBase → Airflow DAG → MinIO que produce el Parquet_MinIO. Este pipeline es externo al Sistema y no es responsabilidad del backend FastAPI.

---

## Requisitos

### Requisito 1: Carga del Dataset desde MinIO

**User Story:** Como usuario del sistema, quiero que el backend cargue el dataset clínico desde MinIO, para que los datos estén disponibles en memoria sin necesidad de una base de datos relacional.

#### Criterios de Aceptación

1. WHEN el Sistema recibe una solicitud a cualquier endpoint que requiera datos, THE Sistema SHALL invocar `get_df()` para obtener el Dataset desde la Cache_DF o desde MinIO si la caché está vacía.
2. WHEN la Cache_DF está vacía, THE Sistema SHALL conectarse al servidor MinIO en `localhost:9000`, listar los objetos del bucket `diabetes-data` con prefijo `stage/`, seleccionar el archivo `.parquet` con la fecha de modificación más reciente y cargarlo en memoria como DataFrame de pandas.
3. WHEN el Parquet_MinIO es cargado exitosamente, THE Sistema SHALL almacenar el DataFrame resultante en la Cache_DF para que solicitudes posteriores no requieran una nueva descarga desde MinIO.
4. WHEN el Usuario activa la recarga del dataset mediante `POST /api/cargar-dataset`, THE Sistema SHALL limpiar la Cache_DF (asignarla a `None`) y forzar una nueva descarga del Parquet_MinIO desde MinIO.
5. WHEN la recarga es exitosa, THE Sistema SHALL retornar HTTP 200 con los campos `ok: true`, `registros` (número de filas del Dataset) y `columnas` (lista de nombres de columnas).
6. IF el bucket `diabetes-data/stage/` no contiene ningún objeto, THEN THE Sistema SHALL retornar HTTP 404 con `detail` igual a "No hay archivos parquet en MinIO stage/".
7. IF el bucket `diabetes-data/stage/` contiene objetos pero ninguno tiene extensión `.parquet`, THEN THE Sistema SHALL retornar HTTP 404 con `detail` igual a "No se encontraron archivos .parquet".
8. IF la conexión a MinIO falla por cualquier causa (servidor no disponible, credenciales incorrectas, etc.), THEN THE Sistema SHALL propagar la excepción como HTTP 500 con `detail` describiendo el error de conexión.
9. WHILE la recarga está en progreso, THE Frontend SHALL deshabilitar el botón de recarga y mostrar un spinner dentro del botón en lugar del ícono habitual.
10. WHEN la recarga finaliza (con éxito o con error), THE Frontend SHALL mostrar el resultado en el área de alerta, aplicar el estilo de error si la respuesta no es HTTP 200, y rehabilitar el botón restaurando su ícono original.

---

### Requisito 2: Consulta de Tablas Virtuales

**User Story:** Como usuario del sistema, quiero explorar el contenido de cualquier Tabla_Virtual generada en memoria, para que pueda verificar los datos y entender la estructura del modelo dimensional.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer un endpoint `GET /api/tabla/{nombre}` que acepte el nombre de una Tabla_Virtual y un parámetro de consulta opcional `limit` con valor por defecto de 50 y rango válido de 1 a 500 inclusive.
2. WHEN el Usuario solicita una tabla con un `limit` válido, THE Sistema SHALL retornar las primeras `limit` filas de la Tabla_Virtual junto con el total de filas de esa tabla en los campos `rows` y `total` respectivamente.
3. WHEN el Usuario solicita una tabla, THE Sistema SHALL retornar las filas como una lista de objetos JSON donde cada clave es el nombre de columna del DataFrame generado.
4. IF el nombre de tabla solicitado no pertenece al TABLAS_MAP, THEN THE Sistema SHALL retornar HTTP 400 con `detail` indicando las opciones válidas, sin generar ningún DataFrame.
5. THE Sistema SHALL incluir en el TABLAS_MAP exactamente las siguientes 6 tablas: `diabetes_dataset`, `dim_paciente`, `dim_ubicacion`, `dim_raza`, `dim_condicion`, `fact_diabetes`.
6. IF el parámetro `limit` es menor que 1, mayor que 500 o no es un entero, THEN THE Sistema SHALL retornar HTTP 422 con un mensaje de validación descriptivo.
7. IF la carga del Dataset desde MinIO falla al procesar la solicitud de tabla, THEN THE Sistema SHALL propagar el error HTTP correspondiente (404 o 500) sin retornar filas parciales.
8. WHEN el Frontend recibe los datos de una tabla con al menos una fila, THE Frontend SHALL renderizar una tabla HTML con los nombres de columna como encabezados `<th>` y los valores de cada fila en celdas `<td>` correspondientes.
9. WHEN el Frontend recibe los datos de una tabla, THE Frontend SHALL mostrar el texto "N de M registros · K columnas" donde N es el número de filas recibidas, M es el total y K es el número de columnas.
10. IF la tabla solicitada no contiene registros (`total` es 0), THEN THE Frontend SHALL mostrar un estado vacío en lugar de la tabla HTML.

---

### Requisito 3: Estadísticas del Sistema

**User Story:** Como usuario del sistema, quiero ver un resumen del estado del Dataset en el Dashboard, para que pueda conocer cuántos registros existen en el dataset y en cada Tabla_Virtual sin consultarlas individualmente.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer un endpoint `GET /api/stats` que retorne un objeto JSON con exactamente 8 claves: `diabetes_dataset`, `dim_paciente`, `dim_ubicacion`, `dim_raza`, `dim_condicion`, `fact_diabetes`, `total_con_diabetes`, `total_sin_diabetes`.
2. WHEN el endpoint `/api/stats` es invocado, THE Sistema SHALL generar cada Tabla_Virtual a partir del Dataset en memoria y retornar el conteo de filas de cada una, junto con los conteos de registros con y sin diabetes de la columna `diabetes` del Dataset.
3. WHEN el Usuario navega al Dashboard o cuando la página carga por primera vez, THE Frontend SHALL invocar automáticamente el endpoint `/api/stats` y renderizar una tarjeta visual por cada clave con su etiqueta legible (distinta del nombre técnico) y el conteo formateado con separadores de miles.
4. IF el endpoint `/api/stats` responde con un error de red o un código HTTP no-2xx (incluyendo errores de MinIO), THEN THE Frontend SHALL mostrar una tarjeta de error indicando ausencia de conexión.

---

### Requisito 4: Visualizaciones Analíticas

**User Story:** Como usuario del sistema, quiero ver gráficas analíticas sobre los datos clínicos, para que pueda identificar patrones en diagnósticos por año, distribución geográfica y distribución de BMI.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer un endpoint `GET /api/chart/diabetes-por-anio` que retorne una lista de objetos JSON con los campos `anio`, `con_diabetes` y `sin_diabetes`, agrupando el Dataset por la columna `year`.
2. WHEN el endpoint `/api/chart/diabetes-por-anio` es invocado con datos disponibles, THE Sistema SHALL retornar los objetos ordenados de forma ascendente por el campo `anio`.
3. THE Sistema SHALL exponer un endpoint `GET /api/chart/pacientes-por-ubicacion` que retorne una lista de hasta 15 objetos JSON con los campos `ubicacion` y `total`, agrupando el Dataset por la columna `location`.
4. WHEN el endpoint `/api/chart/pacientes-por-ubicacion` es invocado con datos disponibles, THE Sistema SHALL retornar los objetos ordenados de forma descendente por el campo `total`.
5. THE Sistema SHALL exponer un endpoint `GET /api/chart/distribucion-bmi` que retorne una lista de objetos JSON con los campos `categoria` y `total`, clasificando los registros del Dataset en 6 rangos de BMI: `<18.5`, `18.5-25`, `25-30`, `30-35`, `35-40`, `>40`.
6. THE Sistema SHALL exponer un endpoint `GET /api/chart/glucosa-vs-diabetes` que retorne una lista de 2 objetos JSON con los campos `diabetes` (valores `"Con diabetes"` y `"Sin diabetes"`) y `glucosa_promedio`, calculando el promedio de `blood_glucose_level` por grupo.
7. IF cualquiera de los cuatro endpoints de chart es invocado y el Dataset está vacío o no disponible, THEN THE Sistema SHALL retornar una lista vacía `[]` con HTTP 200 o propagar el error HTTP de MinIO según corresponda.

---

### Requisito 5: CRUD sobre fact_diabetes

**User Story:** Como usuario del sistema, quiero poder leer, actualizar y eliminar registros individuales de la tabla de hechos en memoria, para que pueda corregir datos clínicos sin necesidad de modificar el archivo fuente en MinIO.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer un endpoint `GET /api/fact/{id_fact}` que retorne el registro completo del Dataset en la posición `id_fact` como objeto JSON.
2. IF `id_fact` es menor que 0 o mayor o igual al número de filas del Dataset, THEN THE Sistema SHALL retornar HTTP 404 con `detail` igual a "Registro no encontrado".
3. THE Sistema SHALL exponer un endpoint `PUT /api/fact/{id_fact}` que acepte como query params opcionales `bmi` (float), `hbA1c_level` (float), `blood_glucose_level` (int) y `diabetes` (int), y actualice los campos provistos en la Cache_DF en la posición `id_fact`.
4. WHEN el `PUT /api/fact/{id_fact}` es exitoso, THE Sistema SHALL retornar HTTP 200 con `ok: true` y el registro actualizado completo en el campo `registro`.
5. THE Sistema SHALL exponer un endpoint `DELETE /api/fact/{id_fact}` que elimine la fila en la posición `id_fact` de la Cache_DF y reindexe el DataFrame resultante.
6. WHEN el `DELETE /api/fact/{id_fact}` es exitoso, THE Sistema SHALL retornar HTTP 200 con `ok: true` y el número de registros restantes en el campo `registros_restantes`.
7. IF `id_fact` no existe para `PUT` o `DELETE`, THEN THE Sistema SHALL retornar HTTP 404 con `detail` igual a "Registro no encontrado".
8. WHEN el Frontend ejecuta una operación CRUD exitosa, THE Frontend SHALL mostrar un mensaje de confirmación con estilo verde durante 5 segundos y luego ocultarlo automáticamente.
9. WHEN el Frontend ejecuta una operación CRUD fallida, THE Frontend SHALL mostrar el campo `detail` del error con estilo rojo durante 5 segundos.

---

### Requisito 6: Información Corporativa

**User Story:** Como usuario del sistema, quiero consultar la información corporativa de DiabCare Analytics, para que pueda conocer la misión, visión y objetivos estratégicos de la empresa.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer un endpoint `GET /api/empresa` que retorne un objeto JSON con exactamente los campos: `nombre` (string), `slogan` (string), `mision` (string), `vision` (string), `objetivos_estrategicos` (array), `objetivos_tacticos` (array) y `objetivos_operacionales` (array).
2. THE Sistema SHALL retornar exactamente 3 elementos en `objetivos_estrategicos`, 3 en `objetivos_tacticos` y 3 en `objetivos_operacionales`.
3. WHEN el Usuario navega a la sección "Empresa", THE Frontend SHALL mostrar `mision` y `vision` en tarjetas HTML visualmente separadas, cada una con un encabezado identificador.
4. WHEN el Usuario navega a la sección "Objetivos", THE Frontend SHALL mostrar los tres arrays de objetivos en secciones diferenciadas con encabezados "Estratégicos", "Tácticos" y "Operacionales".
5. WHEN el Frontend ya ha cargado los datos de empresa en la variable `empresaData`, THE Frontend SHALL reutilizar esa variable sin realizar una nueva petición HTTP al endpoint `/api/empresa` al navegar entre las secciones Empresa y Objetivos.

---

### Requisito 7: Pipeline Externo y Visualización de Arquitectura

**User Story:** Como usuario del sistema, quiero ver el flujo de datos del pipeline externo, para que pueda entender cómo los datos llegan desde PocketBase hasta el backend FastAPI.

#### Criterios de Aceptación

1. THE Frontend SHALL mostrar en la sección "Pipeline" el flujo de datos: PocketBase → Airflow DAG → Parquet → MinIO Stage → FastAPI, con el nombre de cada componente y su dirección (host:puerto o identificador).
2. THE Frontend SHALL mostrar una descripción de cada componente del pipeline: PocketBase (fuente de datos), Airflow (orquestador del DAG `diabetes_pipeline`), MinIO (object storage con bucket `diabetes-data/stage/`), FastAPI (backend que lee el parquet).
3. THE Frontend SHALL incluir en la sección "Pipeline" el botón de recarga del dataset que invoca `POST /api/cargar-dataset` para forzar la descarga del parquet más reciente desde MinIO.

---

### Requisito 8: Rendimiento de Carga (RNF-01)

**User Story:** Como usuario del sistema, quiero que la carga del dataset desde MinIO se complete en un tiempo razonable, para que el sistema esté disponible rápidamente tras el primer acceso.

#### Criterios de Aceptación

1. WHEN el Sistema descarga y carga en memoria el Parquet_MinIO con ~100,000 registros, THE Sistema SHALL completar la operación en menos de 30 segundos en condiciones normales de red local.
2. WHEN la Cache_DF ya está poblada, THE Sistema SHALL responder a cualquier endpoint de datos sin realizar ninguna descarga adicional desde MinIO, con tiempo de respuesta inferior a 2 segundos para operaciones de agregación sobre el Dataset completo.

---

### Requisito 9: Seguridad Básica de Acceso a Datos (RNF-02)

**User Story:** Como administrador del sistema, quiero que solo las tablas autorizadas sean accesibles vía API, para que no se pueda acceder a datos arbitrarios del Dataset.

#### Criterios de Aceptación

1. THE Sistema SHALL validar el nombre de tabla recibido en el endpoint `GET /api/tabla/{nombre}` contra el TABLAS_MAP antes de generar ningún DataFrame.
2. IF el nombre de tabla no pertenece al TABLAS_MAP, THEN THE Sistema SHALL retornar HTTP 400 sin ejecutar ninguna operación sobre el Dataset.
3. THE Sistema SHALL exponer las credenciales de MinIO únicamente como variables de configuración en el código del servidor, nunca en respuestas de la API ni en el frontend.

---

### Requisito 10: Usabilidad e Interfaz (RNF-03)

**User Story:** Como usuario del sistema, quiero una interfaz visual clara y con retroalimentación durante operaciones, para que pueda navegar cómodamente y saber en todo momento el estado del sistema.

#### Criterios de Aceptación

1. THE Frontend SHALL aplicar un tema oscuro (dark theme) usando variables CSS con los colores base `#04080f` (fondo principal) y `#0ef` (color de acento primario).
2. THE Frontend SHALL organizar la navegación en una barra lateral (sidebar) fija con acceso a las secciones: Dashboard, Ver Tablas, CRUD Fact, Pipeline, Empresa y Objetivos.
3. WHEN el Usuario selecciona un ítem de navegación, THE Frontend SHALL mostrar únicamente la sección correspondiente y SHALL aplicar la clase CSS `active` al ítem seleccionado, incluyendo el indicador visual lateral (borde izquierdo de color acento).
4. WHEN una operación de red está en progreso, THE Frontend SHALL mostrar un indicador visual (spinner) hasta que la respuesta sea recibida, momento en que el indicador SHALL desaparecer.
5. WHERE el ancho de pantalla es inferior a 1200px, THE Frontend SHALL reorganizar las cuadrículas de dos columnas en una sola columna; WHERE el ancho es inferior a 900px, THE Frontend SHALL reducir el ancho del sidebar a 200px y ajustar el margen del contenido principal.

---

### Requisito 11: Confiabilidad y Manejo de Errores (RNF-04)

**User Story:** Como usuario del sistema, quiero que los errores sean comunicados con mensajes descriptivos, para que pueda entender qué falló y tomar acción sin necesidad de revisar los logs del servidor.

#### Criterios de Aceptación

1. IF el Dataset no está disponible (MinIO inaccesible o sin archivos parquet) al invocar `/api/stats`, THEN THE Sistema SHALL propagar el error HTTP de MinIO con `detail` descriptivo.
2. IF el Frontend no puede conectarse al servidor al cargar las estadísticas del Dashboard, THEN THE Frontend SHALL mostrar una tarjeta de error indicando ausencia de conexión.
3. IF el Frontend no puede conectarse al servidor al cargar una tabla, THEN THE Frontend SHALL mostrar el mensaje de error en el área de visualización de la tabla, reemplazando cualquier contenido previo.
4. WHEN el backend retorna un error en cualquier operación CRUD, THE Frontend SHALL mostrar el contenido del campo `detail` con el color definido por la variable CSS `--accent3`.
5. THE Sistema SHALL retornar respuestas de error en formato JSON con el campo `detail` conteniendo una cadena no vacía con una descripción legible del error para todos los endpoints de la API.
