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
- **Cache_DF**: La variable global `_df_cache` en `backend/Principal.py` que almacena el DataFrame en memoria tras la primera carga desde MinIO.
- **Tabla_Virtual**: Cada una de las 6 vistas tabulares generadas en memoria por pandas a partir del Dataset: `diabetes_dataset`, `dim_paciente`, `dim_ubicacion`, `dim_raza`, `dim_condicion`, `fact_diabetes`.
- **dim_paciente**: Dimensión de pacientes con columnas `id_paciente`, `gender`, `age`.
- **dim_ubicacion**: Dimensión de ubicaciones con columnas `id_ubicacion`, `location`, `year`.
- **dim_raza**: Dimensión de razas con columnas `id_raza` y las columnas de raza del dataset (`race_AfricanAmerican`, `race_Asian`, `race_Caucasian`, `race_Hispanic`, `race_Other`).
- **dim_condicion**: Dimensión de condiciones preexistentes con columnas `id_condicion`, `hypertension`, `heart_disease`, `smoking_history`.
- **fact_diabetes**: Tabla de hechos con columnas `id_fact`, `bmi`, `hbA1c_level`, `blood_glucose_level`, `diabetes`.
- **TABLAS_MAP**: El diccionario Python en `backend/Principal.py` que mapea nombres de tabla a funciones generadoras de DataFrames. Define la whitelist de tablas accesibles.
- **Dashboard**: La sección principal del frontend que muestra tarjetas de estadísticas del Dataset y las Tablas_Virtuales.
- **Frontend**: La interfaz de usuario SPA servida como plantilla Jinja2 (`frontend/paginas/Inicio.html`).
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
8. IF la conexión a MinIO falla por cualquier causa, THEN THE Sistema SHALL propagar la excepción como HTTP 500 con `detail` describiendo el error de conexión.
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
9. WHEN el Frontend recibe los datos de una tabla, THE Frontend SHALL mostrar el texto "N de M registros · K columnas".
10. IF la tabla solicitada no contiene registros (`total` es 0), THEN THE Frontend SHALL mostrar un estado vacío en lugar de la tabla HTML.

---

### Requisito 3: Estadísticas del Sistema

**User Story:** Como usuario del sistema, quiero ver un resumen del estado del Dataset en el Dashboard, para que pueda conocer cuántos registros existen en el dataset y en cada Tabla_Virtual sin consultarlas individualmente.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer un endpoint `GET /api/stats` que retorne un objeto JSON con exactamente 8 claves: `diabetes_dataset`, `dim_paciente`, `dim_ubicacion`, `dim_raza`, `dim_condicion`, `fact_diabetes`, `total_con_diabetes`, `total_sin_diabetes`.
2. WHEN el endpoint `/api/stats` es invocado, THE Sistema SHALL generar cada Tabla_Virtual a partir del Dataset en memoria y retornar el conteo de filas de cada una.
3. WHEN el Usuario navega al Dashboard, THE Frontend SHALL invocar automáticamente el endpoint `/api/stats` y renderizar una tarjeta visual por cada clave.
4. IF el endpoint `/api/stats` responde con un error, THEN THE Frontend SHALL mostrar una tarjeta de error indicando ausencia de conexión.

---

### Requisito 4: Visualizaciones Analíticas

**User Story:** Como usuario del sistema, quiero ver gráficas analíticas sobre los datos clínicos, para que pueda identificar patrones en diagnósticos por año, distribución geográfica y distribución de BMI.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/chart/diabetes-por-anio` que retorne objetos con `anio`, `con_diabetes` y `sin_diabetes`, ordenados ascendentemente por `anio`.
2. THE Sistema SHALL exponer `GET /api/chart/pacientes-por-ubicacion` que retorne hasta 15 objetos con `ubicacion` y `total`, ordenados descendentemente por `total`.
3. THE Sistema SHALL exponer `GET /api/chart/distribucion-bmi` que retorne objetos con `categoria` y `total`, clasificando registros en 6 rangos de BMI: `<18.5`, `18.5-25`, `25-30`, `30-35`, `35-40`, `>40`.
4. THE Sistema SHALL exponer `GET /api/chart/glucosa-vs-diabetes` que retorne 2 objetos con `diabetes` y `glucosa_promedio`.
5. IF cualquier endpoint de chart es invocado y el Dataset no está disponible, THEN THE Sistema SHALL retornar `[]` con HTTP 200.

---

### Requisito 5: CRUD sobre fact_diabetes

**User Story:** Como usuario del sistema, quiero poder leer, actualizar y eliminar registros individuales de la tabla de hechos en memoria, para que pueda corregir datos clínicos sin necesidad de modificar el archivo fuente en MinIO.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/fact/{id_fact}` que retorne el registro completo del Dataset en la posición `id_fact` como objeto JSON.
2. IF `id_fact` está fuera de rango, THEN THE Sistema SHALL retornar HTTP 404 con `detail` igual a "Registro no encontrado".
3. THE Sistema SHALL exponer `PUT /api/fact/{id_fact}` que actualice los campos provistos (`bmi`, `hbA1c_level`, `blood_glucose_level`, `diabetes`) en la Cache_DF.
4. THE Sistema SHALL exponer `DELETE /api/fact/{id_fact}` que elimine la fila y reindexee el DataFrame.
5. WHEN el Frontend ejecuta una operación CRUD exitosa, THE Frontend SHALL mostrar confirmación verde durante 5 segundos.
6. WHEN el Frontend ejecuta una operación CRUD fallida, THE Frontend SHALL mostrar `detail` del error en rojo durante 5 segundos.

---

### Requisito 6: Información Corporativa

**User Story:** Como usuario del sistema, quiero consultar la información corporativa de DiabCare Analytics, para que pueda conocer la misión, visión y objetivos estratégicos de la empresa.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/empresa` que retorne: `nombre`, `slogan`, `mision`, `vision`, `objetivos_estrategicos`, `objetivos_tacticos`, `objetivos_operacionales`.
2. Cada array de objetivos SHALL tener exactamente 3 elementos.
3. THE Frontend SHALL mostrar `mision` y `vision` en tarjetas separadas con encabezados identificadores.
4. THE Frontend SHALL reutilizar la variable `empresaData` sin nueva petición HTTP al navegar entre Empresa y Objetivos.

---

### Requisito 7: Pipeline Externo y Visualización de Arquitectura

**User Story:** Como usuario del sistema, quiero ver el flujo de datos del pipeline externo, para que pueda entender cómo los datos llegan desde PocketBase hasta el backend FastAPI.

#### Criterios de Aceptación

1. THE Frontend SHALL mostrar el flujo: PocketBase → Airflow DAG → Parquet → MinIO Stage → FastAPI.
2. THE Frontend SHALL incluir el botón de recarga del dataset que invoca `POST /api/cargar-dataset`.

---

### Requisito 8: Rendimiento (RNF-01)

1. Carga del Parquet con ~100,000 registros SHALL completarse en menos de 30 segundos.
2. Con Cache_DF poblada, respuesta a endpoints de datos SHALL ser inferior a 2 segundos.

---

### Requisito 9: Seguridad Básica (RNF-02)

1. THE Sistema SHALL validar el nombre de tabla contra TABLAS_MAP antes de generar ningún DataFrame.
2. IF el nombre no pertenece al TABLAS_MAP, THE Sistema SHALL retornar HTTP 400 sin ejecutar operaciones sobre el Dataset.

---

### Requisito 10: Usabilidad (RNF-03)

1. THE Frontend SHALL aplicar tema oscuro con `#04080f` (fondo) y `#0ef` (acento).
2. THE Frontend SHALL organizar navegación en sidebar fijo con secciones: Dashboard, Ver Tablas, CRUD Fact, Pipeline, Empresa y Objetivos.
3. THE Frontend SHALL mostrar spinner durante operaciones de red en progreso.
