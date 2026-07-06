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

## Flujo de Datos

`
PocketBase → Airflow (DAGs) → Parquet (stage/) → MinIO → FastAPI → Frontend
`

## Paquetes funcionales (P1-P15)

Detalle en specs/003-operativo/paquetes/. Identificadores P1-P15 en SDD; carpetas solo por nombre de modulo.

### Arbol del repositorio

```
diabcare/
+-- backend/
|   +-- Principal.py
|   +-- nucleo/              modelos DWH, utilidades
|   +-- paquetes/
|       +-- autenticacion/   P1
|       +-- usuarios/        P2
|       +-- registros_clinicos/  P3
|       +-- dataset/         P4
|       +-- prediccion/      P6
|       +-- reportes/        P7
|       +-- pipeline_elt/    P8
|       +-- auditoria/       P11
|       +-- configuracion/   P12
|       +-- modelo_ml/       P14
|       +-- clinico/         CU-O02-O04
|           +-- pacientes/
|           +-- admisiones/
|           +-- citas/
+-- frontend/paginas/
    +-- seguridad/   P1, P2
    +-- clinico/     P3, P5-P7 + pacientes/admisiones/agenda
    +-- datos/       P4, P8, P14
    +-- gobierno/    P11, P12
```

Ver tabla completa en specs/000-sistema-general/spec.md seccion 5.1.

## Estructura del proyecto

`
diabcare/
├── backend/
│   ├── Principal.py
│   ├── nucleo/          # modelos DWH, utilidades (JWT, Parquet)
│   └── paquetes/        # un folder por paquete (Rutas + Servicio)
├── frontend/
│   ├── paginas/
│   │   ├── seguridad/   # P1, P2
│   │   ├── clinico/      # P3, P5–P7 + pacientes/admisiones/agenda
│   │   ├── datos/       # P4, P8, P14
│   │   └── gobierno/    # P11, P12
│   └── estaticos/
├── specs/               # especificaciones SDD
├── .cursor/ .specify/   # Spec Kit
└── pruebas/             # pytest
`

## Arranque rápido

`ash
docker compose up -d
cd backend
pip install -r requirements.txt
py -3 Principal.py
`

- **App:** http://localhost:8000  
- **Admin:** dmin@diabcare.com / Admin2026*

## Pruebas

`ash
cd backend
py -m pytest ../pruebas/api -q
`

## Spec-Driven Development

Metodología **Spec Kit** en Cursor: /speckit-constitution, /speckit-specify, /speckit-plan, /speckit-tasks. Artefactos en specs/.
