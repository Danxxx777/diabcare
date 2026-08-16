# Especificación General del Sistema: DiabCare Analytics

**Nivel**: Sistema (paraguas de todos los niveles empresariales)

**Creado**: 2026-06-19

**Estado**: Vigente

**Fuentes**: `README.md`, `docs/TA06_DiabCare.pdf`, `documentacion/EsquemaFactDimensiones.md`,
`specs/000-sistema-general/constitution.md`, código en `backend/` y `frontend/`.

## 1. Nombre del sistema

DiabCare Analytics - Plataforma SaaS de análisis clínico de datos de diabetes
hospitalaria.

## 2. Objetivo general

Unificar la operación hospitalaria de una clínica especializada en diabetes con
analítica, data warehouse (ELT) y Machine Learning, escalando como SaaS. El
objetivo de negocio (TA06) es la expansión internacional vía growth digital,
APIs, nube e inteligencia de negocio (BI).

- **Misión**: Unificar la operación de una clínica especializada en diabetes
  - recepción, consulta, laboratorio, farmacia, facturación y seguimiento - con
  analítica táctica, data warehouse e inteligencia artificial, para que cada
  rol del equipo actúe a tiempo y mejore el control del paciente.
- **Visión**: Ser la plataforma hospitalaria-analítica de referencia en
  diabetes: un SaaS que conecta cuidado continuo, datos confiables y predicción
  clínica, escalable a redes de salud en la región y partners internacionales.

## 3. Actores principales

| Actor | Descripción | Rol técnico |
|-------|-------------|-------------|
| Médico | Registros clínicos, predicciones, análisis y reportes | `medico` |
| Administrador | Usuarios, configuración, auditoría, benchmarking, dataset | `administrador` |
| Analista | Dataset, pipeline ELT, modelo ML, integraciones | `analista` |
| Sistema (Airflow) | Ejecuta el pipeline ELT automatizado | - (proceso) |

Roles válidos definidos en código (`backend/nucleo/utilidades/Dependencias.py`):
`administrador`, `medico`, `analista`.

## 4. Niveles empresariales

Derivados del TA06. La especificación se organiza por nivel (Principio VI de la
constitución):

| Nivel | Horizonte | Objetivos | Casos de uso | Carpeta |
|-------|-----------|-----------|--------------|---------|
| Estratégico | 3-5 años | OE1-OE4 | CU-E01-CU-E08 | `specs/001-estrategico-adm/` |
| Táctico | 6-12 meses | OT1.1-OT4.2 | CU-T01-CU-T10 | `specs/002-tactico/` |
| Operativo | Día a día | OO1.x-OO5.x | CU-O01-CU-O16 | `specs/003-operativo/` |

## 5. Módulos del sistema (15 paquetes funcionales)

El sistema se organiza en 15 paquetes (P1-P15). Estado verificado contra el
código (`backend/Principal.py`, rutas, servicios y páginas frontend) al
2026-06-19:

| Paquete | Nombre | Carpeta | Estado |
|---------|--------|---------|--------|
| P1 | Autenticación y seguridad | `autenticacion` | Implementado |
| P2 | Gestión de usuarios | `usuarios` | Implementado |
| P3 | Gestión de registros clínicos | `registros_clinicos` | Implementado |
| P4 | Dataset y datos sintéticos | `dataset` | Implementado |
| P5 | Análisis y visualización | `analisis` | Implementado (vía endpoints de registros/dataset) |
| P6 | Predicción ML | `prediccion` | Implementado |
| P7 | Reportes | `reportes` | Implementado (entrega GA07 - salida de datos) |
| P8 | Pipeline ELT | `pipeline_elt` | Implementado (entrega GA07 - procesamiento) |
| P9 | Información corporativa | `corporativo` | Planificado (fuera de demo GA07) |
| P10 | Notificaciones y alertas | `notificaciones` | Parcial GA07 (clínicas + Brevo; churn pendiente) |
| P11 | Auditoría y trazabilidad | `auditoria` | Implementado (entrega GA07) |
| P12 | Configuración del sistema | `configuracion` | Implementado (entrega GA07) |
| P13 | Comparación y benchmarking | `benchmarking` | Planificado (fuera de demo GA07) |
| P14 | Gestión del modelo ML | `modelo_ml` | Implementado (entrega GA07 - ciclo ML) |
| P15 | API pública e integraciones | `integraciones` | Planificado (fuera de demo GA07) |

### 5.1 Estructura de código y mapeo de paquetes (2026-07)

Cada paquete agrupa **Rutas + Servicio** en un solo folder de backend. El frontend
se organiza por **departamento**. Los identificadores P1-P15 viven en specs y
trazabilidad; **no** van en nombres de carpeta.

**Árbol del repositorio:**

```
diabcare/
├── backend/
│   ├── Principal.py                 # entrada única FastAPI
│   ├── nucleo/                      # compartido: modelos DWH, utilidades (JWT, Parquet)
│   └── paquetes/                    # 1 carpeta = 1 paquete funcional
│       ├── autenticacion/           # P1
│       ├── usuarios/                # P2
│       ├── registros_clinicos/      # P3
│       ├── dataset/                 # P4
│       ├── prediccion/              # P6
│       ├── reportes/                # P7
│       ├── pipeline_elt/            # P8
│       ├── auditoria/               # P11
│       ├── configuracion/           # P12
│       ├── modelo_ml/               # P14
│       └── clinico/                 # CU-O02-O04
│           ├── pacientes/
│           ├── admisiones/
│           └── citas/
└── frontend/
    ├── estaticos/                   # navegacion.js, api.js, CSS
    └── paginas/
        ├── seguridad/               # P1, P2
        ├── clinico/                 # P3, P5-P7 + pacientes/admisiones/agenda
        ├── datos/                   # P4, P8, P14
        └── gobierno/                # P11, P12
```

**Mapeo completo P1-P15 → rutas en código:**

| Paq. | Nombre | Departamento | Backend (`backend/paquetes/…`) | Frontend (`frontend/paginas/…`) | Estado |
|:----:|--------|--------------|--------------------------------|----------------------------------|--------|
| P1 | Autenticación | Seguridad | `autenticacion/` | `seguridad/autenticacion/` | ✅ |
| P2 | Usuarios | Seguridad | `usuarios/` | `seguridad/usuarios/` | ✅ |
| P3 | Registros clínicos | Clínico | `registros_clinicos/` | `clinico/registros_clinicos/` | ✅ |
| P4 | Dataset / DWH | Datos | `dataset/` | `datos/dataset/` | ✅ |
| P5 | Análisis / BI | Clínico | *(endpoints en P3 y P4)* | `clinico/analisis/` (+ `analisis/estadisticas/`) | ✅ |
| P6 | Predicción ML | Clínico | `prediccion/` | `clinico/prediccion/` | ✅ |
| P7 | Reportes PDF | Clínico | `reportes/` | `clinico/reportes/` | ✅ |
| P8 | Pipeline ELT | Datos | `pipeline_elt/` | `datos/pipeline_elt/` | ✅ |
| P9 | Corporativo | BI | *(planificado)* | - | 🔜 |
| P10 | Notificaciones | Crecimiento | `notificaciones/` | `gobierno/notificaciones/` | ✅ parcial |
| P11 | Auditoría | Gobierno | `auditoria/` | `gobierno/auditoria/` | ✅ |
| P12 | Configuración | Gobierno | `configuracion/` | `gobierno/configuracion/` | ✅ |
| P13 | Benchmarking | BI | *(planificado)* | - | 🔜 |
| P14 | Modelo ML | Datos | `modelo_ml/` | `datos/modelo_ml/` | ✅ |
| P15 | API / integraciones | Crecimiento | *(planificado)* | - | 🔜 |

**Módulos clínicos adicionales (CU-O02-O04):**

| Módulo | Backend | Frontend |
|--------|---------|----------|
| Pacientes / HCE | `clinico/pacientes/` | `clinico/pacientes/` |
| Admisiones | `clinico/admisiones/` | `clinico/admisiones/` |
| Agenda / citas | `clinico/citas/` | `clinico/agenda/` |

Backend compartido: `backend/nucleo/modelos/` (DWH) y `backend/nucleo/utilidades/`
(JWT, `Dependencias.py`, Parquet).

## 6. Departamentos funcionales

Agrupación de paquetes por área (Principio VI de la constitución):

| Departamento | Paquetes | Responsabilidad |
|--------------|----------|-----------------|
| Seguridad e Identidad | P1, P2 | Autenticación, usuarios, roles |
| Operaciones Clínicas | P3, P5, P6, P7, **Pacientes, Admisiones, Citas** | Registros, expediente, agenda, admisiones, análisis, predicción, reportes |
| Datos e Ingeniería | P4, P8, P14 | Dataset, pipeline ELT, modelo ML |
| Inteligencia de Negocio | P9, P13 | Corporativo, benchmarking |
| Gobierno y Cumplimiento | P11, P12 | Auditoría, configuración |
| Crecimiento e Integraciones | P10, P15 | Notificaciones, API pública |

## 7. Arquitectura y flujo de datos

Arquitectura Data Warehouse con modelo Hecho-Dimensión. Flujo de datos:

```
PocketBase → Airflow (DAGs) → Parquet (stage/) → MinIO → FastAPI → Frontend
```

Modelo de datos (ver `documentacion/EsquemaFactDimensiones.md`): 1 tabla de
hechos (`HechosDiabetes`) y 5 dimensiones (`DimensionPaciente`,
`DimensionUbicacion`, `DimensionRaza`, `DimensionCondicion`, `DimensionTiempo`).

Punto de entrada real del backend: `backend/Principal.py`
(`uvicorn Principal:app`). Registra 14 routers de API (P1-P15; P9 Corporativo
añadido en GA07).

### 7.1 Demo GA07 - flujo de datos presentable

Flujo de datos y menú activo (`frontend/estaticos/navegacion.js`):

```
Generador (P4) → Pipeline ELT (P8) → Dataset hecho/dims (P4)
  → Registros / Estadísticas (P3/P5) → Modelo ML (P14) → Predicción (P6)
  → Reportes (P7) → Auditoría (P11)
```

| Módulo | En demo GA07 | Rol principal |
|--------|:---:|---|
| P1 Autenticación | ✅ | Todos |
| P2 Usuarios | ✅ | administrador |
| P3 Registros | ✅ | administrador, medico |
| P4 Dataset + generador | ✅ | administrador, analista |
| P5 Análisis / estadísticas | ✅ | administrador, medico, analista |
| P6 Predicción | ✅ | administrador, medico, analista |
| P7 Reportes | ✅ | administrador, medico |
| P8 Pipeline ELT | ✅ | administrador, analista |
| P11 Auditoría | ✅ | administrador |
| P12 Configuración | ✅ | administrador |
| P14 Modelo ML | ✅ | administrador, analista |
| P9, P10, P13, P15 | ❌ pronto | Iteración posterior |

## 8. Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | HTML5, CSS3, JavaScript (Vanilla) |
| Backend | Python 3, FastAPI, Uvicorn |
| Almacenamiento | MinIO (Parquet columnar) |
| Orquestación ELT | Apache Airflow |
| Fuente | PocketBase |
| ML | scikit-learn |

## 9. Reglas generales

- **RG-001**: Solo usuarios autenticados con JWT (HS256) pueden acceder a los
  módulos. (`backend/paquetes/autenticacion/`)
- **RG-002**: El acceso a cada módulo se restringe por rol según la matriz
  `PERMISOS_MODULOS` (`backend/nucleo/utilidades/Dependencias.py`).
- **RG-003**: Los datos analíticos se leen del Data Warehouse (MinIO/Parquet) y
  no se omite el flujo ELT.
- **RG-004**: El contenido clínico de cara al usuario y los datos sintéticos
  están en español.
- **RG-005**: Las operaciones sensibles (registros, usuarios, configuración)
  deben generar trazas de auditoría.

## 10. Matriz de permisos por módulo

Autoritativa, tomada de `backend/nucleo/utilidades/Dependencias.py` (`PERMISOS_MODULOS`):

| Módulo | administrador | medico | analista |
|--------|:---:|:---:|:---:|
| usuarios | ✅ | | |
| configuracion | ✅ | | |
| auditoria | ✅ | | |
| pacientes | ✅ | ✅ | |
| admisiones | ✅ | | |
| citas (agenda) | ✅ | | |
| registros | ✅ | ✅ | |
| analisis | ✅ | ✅ | ✅ |
| prediccion | ✅ | ✅ | ✅ |
| reportes | ✅ | ✅ | |
| dataset | ✅ | | ✅ |
| pipeline_etl | ✅ | | ✅ |
| modelo_ml | ✅ | | ✅ |
| integraciones | ✅ | | ✅ |
| notificaciones | ✅ | ✅ | ✅ |

> **Mis citas (médico)**: vista en `/paginas/clinico/mis_citas/`; API `GET /api/citas/mis-citas` con `require_medico` (no aparece en `PERMISOS_MODULOS`). Ver `specs/003-operativo/flujo-clinico.md`.

## 11. Restricciones generales

- **RES-001**: El stack tecnológico aprobado no se cambia sin enmienda a la
  constitución.
- **RES-002**: Las contraseñas no se almacenan en texto plano.
- **RES-003**: Metas de desempeño vinculantes (TA06 BSC): latencia P95 < 200 ms,
  uptime ≥ 99.9%, ELT 600K < 15 min, exactitud del modelo de diabetes ≥ 96%.
- **RES-004**: No se programa funcionalidad que no esté especificada
  (Principio I de la constitución).

## 12. Dependencias entre módulos

- P3, P5, P6, P7 dependen de P1 (autenticación) y de datos cargados por P4/P8.
- P5 (análisis) consume estadísticas de P3 y P4.
- P6/P14 (predicción/modelo) dependen del dataset (P4) y del pipeline (P8).
- P7 (reportes) depende de P3, P4, P5 y P6 para componer su contenido.

## 13. Fuera de alcance (de esta especificación general)

- El detalle funcional de cada paquete vive en su propia especificación de nivel
  (`specs/001-estrategico-adm/`, `specs/002-tactico/`, `specs/003-operativo/`).
- Las integraciones externas estratégicas/tácticas (HubSpot, Stripe, BigQuery,
  Kubernetes, CI/CD) se documentan a nivel estratégico/táctico y no forman parte
  del sistema operativo entregable actual.
