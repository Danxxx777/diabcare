# Especificación del Nivel Operativo: DiabCare Analytics

**Nivel empresarial**: Operativo (ejecución día a día)

**Creado**: 2026-06-19

**Estado**: Vigente

**Fuentes**: `TA 06.docx` (Estrategia Documental Empresarial — OE, OT, OO, CU-O),
`specs/000-sistema-general/constitution.md`, código verificado en `backend/` y `frontend/`.

**Casos de uso cubiertos**: CU-O01–CU-O16 + extensiones **CU-O17–CU-O20** (ver `casos-de-uso-correcciones.md`)

> Esta especificación describe el nivel operativo completo. El detalle por
> paquete vive en `specs/003-operativo/paquetes/`. **Flujo clínico**:
> `specs/003-operativo/flujo-clinico.md`. La trazabilidad empresarial completa
> vive en `specs/003-operativo/trazabilidad.md`.

## 1. Objetivo

Definir el comportamiento del sistema en su ejecución diaria: autenticación,
gestión de usuarios y registros clínicos, generación de datos, pipeline ELT,
estadísticas, predicción de diabetes y los casos operativos derivados de los
objetivos estratégicos (growth, APIs, cloud, BI). Corresponde a los objetivos
operativos OO1.x–OO5.x del TA06.

## 2. Contexto

El nivel operativo es la capa de ejecución del negocio. Las decisiones
estratégicas (OE) y tácticas (OT) se materializan aquí en interacciones
concretas actor–sistema. El bloque clínico (OO5.x) está implementado y es el
foco demostrable; los casos de crecimiento e integración (OO1.x–OO4.x) están
especificados para guiar su construcción futura bajo SDD.

## 3. Actores

| Actor | Rol técnico | Casos operativos principales |
|-------|-------------|------------------------------|
| Médico | `medico` | CU-O03, CU-O04, CU-O07, CU-O08, **CU-O20** |
| Administrador | `administrador` | CU-O01, CU-O02, **CU-O17, CU-O18, CU-O19** y acceso total |
| Analista | `analista` | CU-O05, CU-O06, CU-O09 |
| Partner externo | (consumidor API) | CU-O13, CU-O14 |
| Sistema (Airflow) | proceso | CU-O06, CU-O15 |

## 4. Requisitos funcionales (resumen por caso de uso)

Identificadores: `RF-O-{PXX}-NNN`. El detalle (entradas, salidas, escenarios y
criterios) por paquete está en `specs/003-operativo/paquetes/`.

### Departamento: Seguridad e Identidad (P1, P2)

- **RF-O-P01-001** (CU-O01): El sistema DEBE permitir iniciar sesión con email y
  contraseña, emitiendo un token JWT (HS256) con el rol del usuario. *Estado:
  Implementado* (`POST /api/auth/login`).
- **RF-O-P01-002** (CU-O01): El sistema DEBE verificar el token y restringir el
  acceso a módulos según la matriz de permisos. *Implementado*
  (`GET /api/auth/verificar`, `Dependencias.require_modulo`).
- **RF-O-P02-001** (CU-O02): El administrador DEBE poder crear, listar, editar,
  desactivar usuarios y asignar roles. *Implementado* (`/api/usuarios`).
- **RF-O-P02-002** (CU-O02): El sistema DEBE impedir que un administrador se
  desactive o cambie su propio rol. *Implementado*.

### Departamento: Operaciones Clínicas (P3, P5, P6, P7)

- **RF-O-P03-001** (CU-O03): El sistema DEBE permitir CRUD de registros clínicos
  con validación de rangos. *Implementado* (`/api/registros`).
- **RF-O-P03-002** (CU-O04): El sistema DEBE permitir filtrar registros por
  diabetes, género, ubicación y rango de edad. *Implementado*
  (`GET /api/registros/buscar`).
- **RF-O-P05-001** (CU-O07): El sistema DEBE calcular estadísticas clínicas
  (totales, prevalencia, promedios, distribuciones) para visualización.
  *Implementado* (`GET /api/registros/estadisticas`,
  `GET /api/dataset/estadisticas`).
- **RF-O-P05-002** (CU-O10): El sistema DEBE mostrar un dashboard ejecutivo con
  KPIs y alertas clínicas. *Implementado* (`frontend/paginas/clinico/analisis/index.html`).
- **RF-O-P06-001** (CU-O08): El sistema DEBE predecir el riesgo de diabetes a
  partir de variables clínicas, devolviendo probabilidad. *Implementado*
  (`POST /api/prediccion`).
- **RF-O-P06-002** (CU-O09): El sistema DEBE exponer las métricas del modelo
  (exactitud y métricas de clasificación). *Implementado*
  (`GET /api/prediccion/metricas`).
- **RF-O-P07-001** (Reportes): El sistema DEBE generar reportes clínicos en PDF
  descargables con estadísticas, métricas ML y resumen filtrado. *Implementado*
  (`POST /api/reportes/generar`, `specs/003-operativo/paquetes/P07-reportes/spec.md`).

### Departamento: Operaciones Clínicas — Pacientes, Admisiones, Agenda

- **RF-O-PAC-001**: CRUD expedientes paciente (HCE) con foto. *Implementado*
  (`/api/pacientes/`, `P-pacientes-spec.md`).
- **RF-O-ADM-001**: Admisiones hospitalarias solo administrador, médico en select.
  *Implementado* (`/api/admisiones/`, `P-admisiones-spec.md`).
- **RF-O-CIT-001**: Agenda de citas solo administrador. *Implementado*
  (`/api/citas/`, `P-citas-spec.md`).
- **RF-O-CIT-002**: Mis citas para médico (confirmar / atender). *Implementado*
  (`GET /api/citas/mis-citas`, `flujo-clinico.md`).

### Departamento: Datos e Ingeniería (P4, P8, P14)

- **RF-O-P04-001** (CU-O05): El sistema DEBE generar datos sintéticos
  configurables y cargarlos al almacenamiento. *Implementado*
  (`POST /api/dataset/generar`).
- **RF-O-P04-002**: El sistema DEBE exponer hechos y dimensiones del DWH.
  *Implementado* (`/api/dataset/hechos`, `/api/dataset/dimension/*`).
- **RF-O-P08-001** (CU-O06): El sistema DEBE ejecutar y consultar el estado del
  pipeline ELT. *Parcial* — consulta de estado implementada
  (`GET /api/pipeline/estado`); ejecución orquestada vía Airflow (`dags/`).
- **RF-O-P14-001** (CU-O09): El sistema DEBE gestionar el ciclo del modelo ML
  (info, reentrenar, historial). *Implementado* (`/api/modelo-ml/*`).

### Departamento: Inteligencia de Negocio (P9, P13)

- **RF-O-P13-001**: El sistema DEBE permitir comparación/benchmarking entre
  cohortes o periodos. *No implementado* (fuera demo GA07).

### Departamento: Gobierno y Cumplimiento (P11, P12)

- **RF-O-P11-001**: El sistema DEBE registrar y consultar eventos de auditoría.
  *Implementado* (`/api/auditoria/`).
- **RF-O-P12-001**: El sistema DEBE permitir configurar parámetros del sistema.
  *Implementado* (`/api/configuracion/`).

### Departamento: Crecimiento e Integraciones (P10, P15)

- **RF-O-P10-001** (CU-O16): El sistema DEBE emitir notificaciones/alertas
  (p. ej. riesgo). *Parcial* — UI y servicios presentes, sin API REST.
- **RF-O-P15-001** (CU-O13, CU-O14): El sistema DEBE exponer una API pública
  documentada (OpenAPI) para partners. *Parcial* — Swagger/OpenAPI autogenerado
  por FastAPI en `/docs`; programa de partners y endpoints dedicados no
  implementados.
- **RF-O-P15-002** (CU-O11, CU-O12): Registro de leads (HubSpot) y pago de
  suscripción (Stripe). *No implementado* — corresponde a iniciativas
  estratégicas/tácticas; fuera del sistema operativo entregable actual.

## 5. Requisitos no funcionales

- **RNF-O-001** (Seguridad): Todo endpoint protegido DEBE exigir JWT válido; el
  acceso por módulo se rige por `PERMISOS_MODULOS`.
- **RNF-O-002** (Desempeño): La latencia P95 de endpoints públicos DEBE ser
  < 200 ms (meta TA06 BSC).
- **RNF-O-003** (Idioma): La interfaz y los datos sintéticos DEBEN estar en
  español.
- **RNF-O-004** (Trazabilidad): Las operaciones sensibles DEBEN generar eventos
  de auditoría.
- **RNF-O-005** (Privacidad): Los reportes y exportaciones NO DEBEN exponer
  identificadores que permitan reidentificación individual.

## 6. Reglas de negocio

- **RN-O-001**: Un usuario solo accede a los módulos permitidos por su rol.
- **RN-O-002**: Un administrador no puede desactivar ni cambiar el rol de su
  propia cuenta.
- **RN-O-003**: Las predicciones requieren un modelo entrenado disponible; si no
  existe, el sistema indica que debe entrenarse.
- **RN-O-004**: Las lecturas analíticas provienen del DWH (MinIO/Parquet) y no
  omiten el flujo ELT.
- **RN-O-005**: HbA1c promedio > 7.5 se considera señal de alerta clínica.

## 7. Entradas (principales)

Credenciales (email, contraseña); datos de registro clínico (year, gender, age,
location, hypertension, heart_disease, smoking_history, bmi, hbA1c_level,
blood_glucose_level, diabetes); filtros de búsqueda; parámetros de generación de
dataset (cantidad, year); variables de predicción (age, bmi, hbA1c_level,
blood_glucose_level, hypertension, heart_disease).

## 8. Salidas (principales)

Token JWT y datos de sesión; listados y registros clínicos; estadísticas
agregadas (JSON para Chart.js); resultado de predicción con probabilidad;
métricas del modelo; estado del pipeline; (pendiente) reporte PDF.

## 9. Escenarios principales

### Escenario 1: Inicio de sesión exitoso (CU-O01)
- **Dado** un usuario registrado con credenciales válidas,
- **Cuando** envía email y contraseña a `POST /api/auth/login`,
- **Entonces** el sistema responde con un token JWT y el rol, y habilita los
  módulos permitidos por ese rol.

### Escenario 2: CRUD de registro clínico (CU-O03)
- **Dado** un médico autenticado,
- **Cuando** crea un registro clínico con datos válidos,
- **Entonces** el sistema lo persiste y lo devuelve en los listados y búsquedas.

### Escenario 3: Predicción de diabetes (CU-O08)
- **Dado** un modelo entrenado disponible,
- **Cuando** se envían variables clínicas a `POST /api/prediccion`,
- **Entonces** el sistema devuelve el diagnóstico estimado y la probabilidad.

### Escenario 4: Acceso denegado por rol (RN-O-001)
- **Dado** un usuario con rol `analista`,
- **Cuando** intenta acceder al módulo de registros clínicos,
- **Entonces** el sistema responde 403 indicando que su rol no tiene acceso.

## 10. Criterios de aceptación

- **CA-O-001**: Un usuario válido obtiene token y accede solo a sus módulos.
- **CA-O-002**: Un médico completa el ciclo CRUD de un registro clínico.
- **CA-O-003**: La búsqueda filtrada devuelve los registros que cumplen los
  criterios.
- **CA-O-004**: Las estadísticas reflejan los datos reales del DWH.
- **CA-O-005**: Con modelo entrenado, la predicción devuelve probabilidad; sin
  modelo, el sistema indica que debe entrenarse.
- **CA-O-006**: Un rol sin permiso recibe 403 al acceder a un módulo restringido.

## 11. Dependencias

- P3, P5, P6, P7 dependen de P1 (sesión) y de datos cargados por P4/P8.
- P5 (estadísticas) depende de los registros (P3) y del dataset (P4).
- P6/P14 (predicción/modelo) dependen del dataset (P4).
- P7 (reportes) depende de P3, P4, P5 y P6.

## 12. Restricciones

- Stack fijo según constitución (no se cambia sin enmienda).
- Contraseñas nunca en texto plano.
- Entry point único del backend: `backend/Principal.py`
  (`backend/servidor.py` está obsoleto y no debe usarse).

## 13. Fuera de alcance (del sistema operativo entregable actual)

- CU-O11 (lead HubSpot) y CU-O12 (pago Stripe): iniciativas de crecimiento
  (OE1), no implementadas.
- CU-O15 (despliegue CI/CD): infraestructura (OE3), no es funcionalidad de la
  aplicación.
- CU-O16 (alerta churn con ML de negocio): inteligencia de negocio (OE4),
  especificada pero no implementada.
- Programa de partners y API pública dedicada (más allá del Swagger
  autogenerado).
