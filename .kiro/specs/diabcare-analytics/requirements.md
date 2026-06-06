# Documento de Requisitos — DiabCare Analytics v2.0

## Introducción

DiabCare Analytics es una plataforma SaaS académica (6to semestre — Construcción del Software) para la gestión y análisis de datos clínicos de diabetes hospitalaria. El sistema lee archivos `.parquet` almacenados en MinIO, genera estadísticas clínicas con pandas, expone visualizaciones analíticas, gestión de usuarios y registros clínicos con autenticación JWT.

**Stack tecnológico:** FastAPI + Python 3.14 (backend), MinIO (object storage), pandas (transformación ELT), HTML/CSS/JS vanilla (frontend multi-página), PocketBase (usuarios origen), Apache Airflow 2.9.1 (orquestación), Uvicorn (servidor).

---

## Glosario

- **Sistema**: La aplicación web DiabCare Analytics (backend FastAPI + frontend HTML/JS multi-página).
- **API**: Endpoints REST expuestos por el backend FastAPI en `localhost:8000`.
- **MinIO**: Object storage local en `localhost:9000`. Bucket principal: `diabetes-data`, prefijo `stage/`. Bucket app: `diabcare-app`.
- **Dataset**: DataFrame de pandas cargado desde los archivos `.parquet` en MinIO, con registros clínicos de diabetes sintéticos.
- **Token JWT**: Token de autenticación generado al iniciar sesión, válido por 8 horas, almacenado en `localStorage`.
- **Roles**: `administrador`, `medico`, `analista`. Cada rol tiene acceso restringido a módulos específicos.
- **PocketBase**: Base de datos en `localhost:8090` que almacena usuarios originales del sistema.
- **Airflow**: Orquestador de pipelines ELT en Docker que mueve datos de PocketBase a MinIO.

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

---

### Requisito 3: Dataset y Generación de Datos

**User Story:** Como analista, quiero explorar el dataset clínico y generar datos sintéticos para análisis.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/dataset/hechos` con paginación (`skip`, `limit`) que retorne registros del parquet más reciente en MinIO.
2. THE Sistema SHALL exponer `GET /api/dataset/dimension/{nombre}` para las dimensiones: `paciente`, `ubicacion`, `raza`, `condicion`.
3. THE Sistema SHALL exponer `POST /api/dataset/generar` que genere `cantidad` registros sintéticos con distribuciones clínicas reales y los suba a MinIO en formato Parquet.
4. WHEN la generación es exitosa, THE Sistema SHALL retornar `mensaje`, `archivo` (ruta en MinIO) y `total` (registros generados).
5. THE Sistema SHALL generar registros con campos: year, gender (Masculino/Femenino/Otro), age, location (ciudades en español), razas (flags 0/1), hypertension, heart_disease, smoking_history (en español), bmi, hbA1c_level, blood_glucose_level, diabetes.
6. THE Frontend SHALL mostrar presets de cantidad (1K, 10K, 50K, 100K, 500K).
7. THE Frontend SHALL mostrar barra de progreso animada con pasos durante la generación.
8. THE Frontend SHALL mostrar card de resultado con registros generados, año y nombre del archivo.

---

### Requisito 4: Registros Clínicos

**User Story:** Como médico, quiero consultar y filtrar registros clínicos del dataset para análisis específicos.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/registros/` con paginación y retornar `total` y `registros`.
2. THE Sistema SHALL exponer `GET /api/registros/buscar` con filtros opcionales: `diabetes`, `gender`, `location`, `age_min`, `age_max`.
3. THE Sistema SHALL exponer `POST /api/registros/` para crear nuevos registros clínicos.
4. THE Sistema SHALL exponer `PUT /api/registros/{id}` para actualizar campos clínicos (bmi, hbA1c_level, blood_glucose_level, diabetes, hypertension, heart_disease).
5. THE Sistema SHALL exponer `DELETE /api/registros/{id}` para eliminar un registro.
6. THE Frontend SHALL mostrar tabla paginada con navegación anterior/siguiente.
7. THE Frontend SHALL permitir filtros por diabetes, género, ubicación y rango de edad.

---

### Requisito 5: Estadísticas Clínicas

**User Story:** Como analista, quiero ver estadísticas detalladas del dataset para identificar patrones clínicos.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer `GET /api/registros/estadisticas` que retorne datos reales calculados desde el DataFrame.
2. THE endpoint SHALL retornar: total, con_diabetes, sin_diabetes, genero (counts por valor), tabaquismo (con/sin diabetes por valor), razas (con/sin diabetes por raza), edad (con/sin diabetes por rango), promedios (bmi/hba1c/glucosa con/sin diabetes), comorbilidades (hipertension/cardiopatia con/sin diabetes), ubicaciones (top 10), tendencia (por año).
3. THE Frontend SHALL mostrar KPI cards con total, con_diabetes, sin_diabetes, prevalencia.
4. THE Frontend SHALL mostrar indicadores clínicos promedio de BMI, HbA1c y glucosa con/sin diabetes.
5. THE Frontend SHALL mostrar gráficas reales con Chart.js: donut de distribución, barras por género, comorbilidades, edad, raza, tabaquismo, top ubicaciones y tendencia por año.
6. THE Frontend SHALL mostrar barras comparativas inline de promedios clínicos.

---

### Requisito 6: Dashboard Ejecutivo

**User Story:** Como usuario, quiero ver un resumen ejecutivo del sistema al ingresar.

#### Criterios de Aceptación

1. THE Dashboard SHALL consumir `GET /api/registros/estadisticas` y `GET /api/dataset/estadisticas`.
2. THE Dashboard SHALL mostrar 4 KPI cards: total registros, con diabetes, sin diabetes, prevalencia.
3. THE Dashboard SHALL mostrar donut compacto de distribución diabetes con porcentajes.
4. THE Dashboard SHALL mostrar 4 accesos rápidos a: Estadísticas, Registros, Dataset, Generador.
5. THE Dashboard SHALL generar alertas clínicas dinámicas basadas en datos reales (prevalencia, HbA1c, BMI, volumen).
6. THE Dashboard SHALL mostrar promedios clínicos con/sin diabetes.
7. THE Dashboard SHALL mostrar top 6 ubicaciones con barras proporcionales.
8. THE Dashboard SHALL mostrar estado del sistema (MinIO, dataset, API, JWT, ML, Pipeline).
9. THE Dashboard SHALL mostrar últimos archivos en MinIO con columnas del dataset.

---

## Requisitos No Funcionales

### RNF-01: Seguridad
1. Todos los endpoints (excepto `/api/auth/login` y páginas frontend) SHALL requerir token JWT válido.
2. Los roles SHALL restringir acceso a módulos: `usuarios/configuracion/auditoria` → solo administrador; `registros/analisis/prediccion/reportes` → administrador y médico; `dataset/pipeline/modelo_ml` → administrador y analista.
3. Las contraseñas SHALL almacenarse como hash SHA-256, nunca en texto plano.

### RNF-02: Rendimiento
1. Carga del parquet con 100k+ registros SHALL completarse en menos de 30 segundos.
2. Endpoints de estadísticas SHALL responder en menos de 5 segundos con 300k+ registros.

### RNF-03: Usabilidad
1. THE Frontend SHALL aplicar tema oscuro consistente con variables CSS compartidas en `estilos.css`.
2. THE Frontend SHALL mostrar spinners durante operaciones de red.
3. THE Frontend SHALL mostrar toasts de confirmación/error tras operaciones CRUD.
4. THE Sidebar SHALL ser consistente en todas las páginas con el mismo componente HTML.

### RNF-04: Disponibilidad
1. THE Sistema SHALL inicializar el bucket MinIO y el usuario admin automáticamente al arrancar.
2. IF el bucket no existe, THE Sistema SHALL crearlo en el startup sin intervención manual.
