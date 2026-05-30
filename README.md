# DiabCare Analytics

Plataforma SaaS de anÃ¡lisis clÃ­nico de datos de diabetes hospitalaria.  
**59 casos de uso Â· 15 paquetes funcionales Â· Arquitectura Data Warehouse**

## TecnologÃ­as

| Capa | TecnologÃ­a |
|------|-----------|
| Frontend | HTML5 + CSS3 + JavaScript Vanilla |
| Backend | Python 3 + FastAPI + Uvicorn |
| Almacenamiento | MinIO (Parquet columnar) |
| OrquestaciÃ³n ETL | Apache Airflow |
| Fuente de datos | PocketBase |
| Machine Learning | scikit-learn |cd backend

## Modelo de Datos

Arquitectura **Data Warehouse** con 21 tablas: 1 tabla de hechos, 5 dimensiones y 15 tablas operativas.

| Tabla | Tipo | DescripciÃ³n |
|-------|------|-------------|
| `HechosDiabetes` | Hechos | Tabla de hechos principal (encounter_id, glucosa, BMI, HbA1c, diagnÃ³stico) |
| `DimensionPaciente` | DimensiÃ³n | Datos del paciente (gÃ©nero, edad) |
| `DimensionUbicacion` | DimensiÃ³n | UbicaciÃ³n geogrÃ¡fica |
| `DimensionRaza` | DimensiÃ³n | Raza/etnia del paciente |
| `DimensionCondicion` | DimensiÃ³n | CondiciÃ³n mÃ©dica (hipertensiÃ³n, cardiopatÃ­a) |
| `DimensionTiempo` | DimensiÃ³n | AÃ±o del registro clÃ­nico |

## Flujo de Datos

```
PocketBase â†’ Airflow (DAGs) â†’ Parquet (stage/) â†’ MinIO â†’ FastAPI â†’ Frontend
```

## Paquetes de Casos de Uso

El sistema cuenta con **59 casos de uso** organizados en **15 paquetes funcionales**:

| Paquete | Nombre | Carpeta | CUs |
|---------|--------|---------|-----|
| P1 | AutenticaciÃ³n y seguridad | `autenticacion` | CU01â€“CU04 |
| P2 | GestiÃ³n de usuarios | `usuarios` | CU05â€“CU08 |
| P3 | GestiÃ³n de registros clÃ­nicos | `registros_clinicos` | CU09â€“CU13 |
| P4 | Dataset y datos sintÃ©ticos | `dataset` | CU14â€“CU17 |
| P5 | AnÃ¡lisis y visualizaciÃ³n | `analisis` | CU18â€“CU21 |
| P6 | PredicciÃ³n ML | `prediccion` | CU22â€“CU25 |
| P7 | Reportes | `reportes` | CU26â€“CU29 |
| P8 | Pipeline ETL | `pipeline_etl` | CU30â€“CU33 |
| P9 | InformaciÃ³n corporativa | `corporativo` | CU34â€“CU36 |
| P10 | Notificaciones y alertas | `notificaciones` | CU37â€“CU40 |
| P11 | AuditorÃ­a y trazabilidad | `auditoria` | CU41â€“CU44 |
| P12 | ConfiguraciÃ³n del sistema | `configuracion` | CU45â€“CU48 |
| P13 | ComparaciÃ³n y benchmarking | `benchmarking` | CU49â€“CU52 |
| P14 | GestiÃ³n del modelo ML | `modelo_ml` | CU53â€“CU56 |
| P15 | API pÃºblica e integraciones | `integraciones` | CU57â€“CU59 |

## Estructura del Proyecto

```
diabcare/
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ api/               Rutas FastAPI por paquete (P1-P15)
â”‚   â”œâ”€â”€ servicios/         LÃ³gica de negocio por paquete
â”‚   â”œâ”€â”€ modelos/           Modelos de datos (hechos + dimensiones)
â”‚   â””â”€â”€ utilidades/        Helpers, logger, Parquet utils
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ paginas/           PÃ¡ginas HTML por paquete (P1-P15)
â”‚   â”œâ”€â”€ componentes/       Componentes reutilizables por paquete
â”‚   â””â”€â”€ estaticos/         CSS, JS y assets por mÃ³dulo
â”œâ”€â”€ ml/
â”‚   â”œâ”€â”€ modelos/           Entrenador y Predictor (scikit-learn)
â”‚   â”œâ”€â”€ evaluacion/        MÃ©tricas de desempeÃ±o
â”‚   â”œâ”€â”€ datos_entrenamiento/
â”‚   â”œâ”€â”€ versiones/         Versiones del modelo guardadas
â”‚   â””â”€â”€ cuadernos/         AnÃ¡lisis exploratorio (.ipynb)
â”œâ”€â”€ almacenamiento/
â”‚   â”œâ”€â”€ aplicacion/        Buckets: exportaciones, logs, modelos, reportes
â”‚   â””â”€â”€ diabetes-data/     Parquet: etapa, procesados, sintÃ©ticos
â”œâ”€â”€ documentacion/
â”‚   â”œâ”€â”€ casos_de_uso/      Diagramas UML de los 15 paquetes
â”‚   â”œâ”€â”€ diagramas/         ER, arquitectura, flujos
â”‚   â”œâ”€â”€ api/               DocumentaciÃ³n Swagger/OpenAPI
â”‚   â””â”€â”€ entregables/       PDFs y documentos de entrega
â”œâ”€â”€ pruebas/
â”‚   â”œâ”€â”€ api/               Tests de endpoints
â”‚   â”œâ”€â”€ integracion/       Tests de flujo completo
â”‚   â””â”€â”€ ml/                Tests de predicciÃ³n
â”œâ”€â”€ dags/                  DAGs de Apache Airflow
â”œâ”€â”€ config/                ConfiguraciÃ³n global del sistema
â”œâ”€â”€ logs/                  Logs de ejecuciÃ³n (no se suben a Git)
â””â”€â”€ stage/                 Parquet temporal (no se sube a Git)
```

## Actores del Sistema

| Actor | Rol |
|-------|-----|
| MÃ©dico | Registros clÃ­nicos, predicciones, reportes |
| Administrador | Usuarios, configuraciÃ³n, auditorÃ­a, dataset |
| Analista | Dashboards, benchmarking, modelo ML |
| Sistema (Airflow) | Pipeline ETL automatizado |

