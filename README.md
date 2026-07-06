# DiabCare Analytics

Plataforma SaaS de análisis clínico de datos de diabetes hospitalaria.  
**59 casos de uso · 15 paquetes funcionales · Arquitectura Data Warehouse**

Repositorio: [github.com/Danxxx777/diabcare](https://github.com/Danxxx777/diabcare)

## Tecnologías

| Capa | Tecnología |
|------|------------|
| Frontend | HTML5 + CSS3 + JavaScript (Vanilla) |
| Backend | Python 3 + FastAPI + Uvicorn |
| Almacenamiento | MinIO (Parquet columnar) |
| Orquestación ETL | Apache Airflow *(opcional, ver `_futuro/`)* |
| Fuente de datos | PocketBase |
| Machine Learning | scikit-learn |

## Flujo de datos

```
PocketBase → Airflow (DAGs) → Parquet (stage/) → MinIO → FastAPI → Frontend
```

## Flujo clínico (demo)

| Rol | Qué hace | Pantallas |
|-----|----------|-----------|
| **Administrador** | Alta de paciente (HCE), admisiones, agenda con médico asignado | Pacientes, Admisiones, Agenda |
| **Médico** | Ve sus citas, confirma/atiente, documenta consulta | Mis citas, Consultas, Predicción, Reportes |

Detalle en [`specs/003-operativo/flujo-clinico.md`](specs/003-operativo/flujo-clinico.md).

## Paquetes funcionales (P1–P15)

Especificación por paquete en `specs/003-operativo/paquetes/`. Los identificadores P1–P15 viven en specs y trazabilidad; las carpetas de código usan solo el nombre del módulo.

| Paq. | Módulo | Estado |
|:----:|--------|--------|
| P1 | Autenticación | Implementado |
| P2 | Usuarios | Implementado |
| P3 | Registros clínicos (consultas) | Implementado |
| P4 | Dataset / DWH | Implementado |
| P5 | Análisis / BI | Implementado |
| P6 | Predicción ML | Implementado |
| P7 | Reportes PDF | Implementado |
| P8 | Pipeline ELT | Implementado |
| P9 | Corporativo | Planificado (`_futuro/`) |
| P10 | Notificaciones y alertas | Implementado |
| P11 | Auditoría | Implementado |
| P12 | Configuración | Implementado |
| P13 | Benchmarking | Planificado (`_futuro/`) |
| P14 | Modelo ML | Implementado |
| P15 | Integraciones / API partner | Planificado (`_futuro/`) |

**Módulos clínicos adicionales:** Pacientes/HCE, Admisiones, Agenda (`/api/citas`), Mis citas (`/api/mis-citas`).

## Estructura del repositorio

```
diabcare/
├── servidor.py              # arranque desde la raíz
├── backend/
│   ├── Principal.py         # app FastAPI
│   ├── nucleo/              # modelos DWH, JWT, utilidades
│   └── paquetes/
│       ├── autenticacion/   # P1
│       ├── usuarios/        # P2
│       ├── registros_clinicos/  # P3
│       ├── dataset/         # P4
│       ├── prediccion/      # P6
│       ├── reportes/        # P7
│       ├── pipeline_elt/    # P8
│       ├── notificaciones/  # P10
│       ├── auditoria/       # P11
│       ├── configuracion/   # P12
│       ├── modelo_ml/       # P14
│       └── clinico/
│           ├── pacientes/   # HCE + foto MinIO
│           ├── admisiones/
│           └── citas/       # agenda + mis-citas
├── frontend/
│   ├── estaticos/           # navegacion.js, api.js, CSS
│   └── paginas/
│       ├── seguridad/       # login, usuarios, perfil
│       ├── clinico/         # pacientes, agenda, mis citas, consultas, BI…
│       ├── datos/           # dataset, pipeline, modelo ML
│       ├── gobierno/        # auditoría, configuración
│       └── notificaciones/
├── specs/                   # especificaciones SDD (Spec Kit)
└── _futuro/                 # Airflow, pruebas pytest, módulos próximos
```

Tabla completa P1–P15 → rutas en [`specs/000-sistema-general/spec.md`](specs/000-sistema-general/spec.md) (sección 5.1).

## Arranque rápido

**Requisitos:** Python 3.11+, MinIO en marcha (puerto 9000 por defecto).

```bash
# Desde la raíz del repo
pip install -r backend/requirements.txt
py -3 servidor.py
```

Alternativa:

```bash
cd backend
py -3 Principal.py
```

- **App:** http://localhost:8000  
- **API docs:** http://localhost:8000/docs  
- **Admin demo:** `admin@diabcare.com` / `Admin2026*`

MinIO y Airflow en Docker (opcional): ver `_futuro/docker-compose.yaml`.

## Pruebas

Suite pytest en `_futuro/pruebas/`:

```bash
cd backend
py -m pytest ../_futuro/pruebas/api -q
```

## Spec-Driven Development

Metodología **Spec Kit** en Cursor: `/speckit-constitution`, `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`.  
Constitución del proyecto: `.specify/memory/constitution.md`.

## Contexto académico

Proyecto de la materia Construcción de Software — entrega GA07 (DiabCare Analytics).
