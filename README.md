# DiabCare Analytics

Plataforma SaaS de análisis clínico de datos de diabetes hospitalaria.

## Tecnologías
- **Frontend:** HTML5 + CSS3 + JavaScript Vanilla
- **Backend:** Python 3 + FastAPI + Uvicorn
- **Base de datos:** MinIO (Parquet columnar)
- **Orquestación:** Apache Airflow
- **Fuente de datos:** PocketBase
- **Machine Learning:** scikit-learn

## Modelo de Datos
- `HechoDiabetes` — tabla de hechos principal
- `DimPaciente` — dimensión paciente
- `DimUbicacion` — dimensión ubicación geográfica
- `DimRaza` — dimensión raza
- `DimCondicion` — dimensión condición médica
- `DimTiempo` — dimensión tiempo

## Flujo de Datos
PocketBase → Airflow → Parquet (etapa/) → MinIO → FastAPI → Frontend

## Estructura
```
diabcare/
├── backend/         API FastAPI + servicios + modelos + utilidades
├── frontend/        Interfaz web (HTML/CSS/JS Vanilla)
├── ml/              Modelos de predicción (scikit-learn)
├── orquestacion/    DAGs Airflow + scripts ETL
├── almacenamiento/  Estructura de buckets MinIO documentada
├── documentacion/   Diagramas, casos de uso, entregables, BD
├── pruebas/         Tests por módulo
├── configuracion/   Ajustes globales del sistema
└── etapa/           Parquet temporal (no se sube a Git)
```
