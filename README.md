# DiabCare Analytics

Plataforma SaaS de análisis clínico de datos de diabetes hospitalaria.  
**59 casos de uso · 15 paquetes funcionales · Arquitectura Data Warehouse**

## Tecnologías

| Capa | Tecnología |
|------|-----------|
| Frontend | HTML5 + CSS3 + JavaScript Vanilla |
| Backend | Python 3 + FastAPI + Uvicorn |
| Almacenamiento | MinIO (Parquet columnar) |
| Orquestación ETL | Apache Airflow |
| Fuente de datos | PocketBase |
| Machine Learning | scikit-learn |

## Modelo de Datos

Arquitectura **Data Warehouse** con 21 tablas: 1 tabla de hechos, 5 dimensiones y 15 tablas operativas.

| Tabla | Tipo | Descripción |
|-------|------|-------------|
| `HechosDiabetes` | Hechos | Tabla de hechos principal (encounter_id, glucosa, BMI, HbA1c, diagnóstico) |
| `DimensionPaciente` | Dimensión | Datos del paciente (género, edad) |
| `DimensionUbicacion` | Dimensión | Ubicación geográfica |
| `DimensionRaza` | Dimensión | Raza/etnia del paciente |
| `DimensionCondicion` | Dimensión | Condición médica (hipertensión, cardiopatía) |
| `DimensionTiempo` | Dimensión | Año del registro clínico |

## Flujo de Datos

```
PocketBase → Airflow (DAGs) → Parquet (stage/) → MinIO → FastAPI → Frontend
```

## Paquetes de Casos de Uso

El sistema cuenta con **59 casos de uso** organizados en **15 paquetes funcionales**:

| Paquete | Nombre | Carpeta | CUs |
|---------|--------|---------|-----|
| P1 | Autenticación y seguridad | `autenticacion` | CU01–CU04 |
| P2 | Gestión de usuarios | `usuarios` | CU05–CU08 |
| P3 | Gestión de registros clínicos | `registros_clinicos` | CU09–CU13 |
| P4 | Dataset y datos sintéticos | `dataset` | CU14–CU17 |
| P5 | Análisis y visualización | `analisis` | CU18–CU21 |
| P6 | Predicción ML | `prediccion` | CU22–CU25 |
| P7 | Reportes | `reportes` | CU26–CU29 |
| P8 | Pipeline ETL | `pipeline_etl` | CU30–CU33 |
| P9 | Información corporativa | `corporativo` | CU34–CU36 |
| P10 | Notificaciones y alertas | `notificaciones` | CU37–CU40 |
| P11 | Auditoría y trazabilidad | `auditoria` | CU41–CU44 |
| P12 | Configuración del sistema | `configuracion` | CU45–CU48 |
| P13 | Comparación y benchmarking | `benchmarking` | CU49–CU52 |
| P14 | Gestión del modelo ML | `modelo_ml` | CU53–CU56 |
| P15 | API pública e integraciones | `integraciones` | CU57–CU59 |

## Estructura del Proyecto

```
diabcare/
├── backend/
│   ├── api/               Rutas FastAPI por paquete (P1–P15)
│   ├── servicios/         Lógica de negocio por paquete
│   ├── modelos/           Hechos y dimensiones (Data Warehouse)
│   └── utilidades/        JWT, Parquet, logger
├── frontend/
│   ├── paginas/           Páginas HTML por paquete (P1–P15)
│   └── estaticos/         CSS, JS compartidos (navegación, estilos)
├── specs/                 Especificaciones SDD (entrega académica)
│   ├── requirements.md    Requisitos consolidados (R)
│   ├── design.md          Diseño y arquitectura (D)
│   ├── tasks.md           Plan de implementación (T)
│   ├── 000-sistema-general/
│   └── 003-operativo/     Spec operativa y paquetes P01–P15
├── .cursor/               Spec Kit — skills /speckit-* para Cursor
├── .specify/              Spec Kit — plantillas, scripts, constitución
├── pruebas/               pytest (API por módulo)
├── ml/                    Entrenamiento y evaluación ML
├── docker-compose.yaml    MinIO, PocketBase, Airflow
└── pipeline_diabetes.py   DAG ETL de referencia
```

## Actores del Sistema

| Actor | Rol |
|-------|-----|
| Médico | Registros clínicos, predicciones, reportes |
| Administrador | Usuarios, configuración, auditoría, dataset |
| Analista | Dashboards, benchmarking, modelo ML |
| Sistema (Airflow) | Pipeline ETL automatizado |

## Arranque rápido

```bash
docker compose up -d
cd backend
pip install -r requirements.txt
uvicorn Principal:app --reload --port 8000
```

- **App:** http://localhost:8000  
- **Admin:** `admin@diabcare.com` / `Admin2026*`

## Pruebas

```bash
cd backend
py -m pytest ../pruebas/api -q
```

## Spec-Driven Development

Metodología **Spec Kit** (GitHub): usar en Cursor los skills `/speckit-constitution`, `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`. Los artefactos de presentación viven en `specs/`; la herramienta en `.cursor/` y `.specify/`.
