# Plan de Implementación: P7 — Reportes PDF

**Paquete**: P7 (Operaciones Clínicas) · **Nivel**: Operativo

**Fecha**: 2026-06-19 · **Spec**: `spec.md`

**Entrada**: Especificación de `specs/003-operativo/paquetes/P07-reportes/spec.md`

## Resumen

Implementar el módulo de Reportes PDF: generación on-demand de un PDF clínico
en español que combina (1) estadísticas del dataset, (2) métricas del modelo de
predicción y (3) un resumen de registros filtrados; con persistencia en MinIO,
listado e historial de descarga, y control de acceso por rol. Se reutilizan los
servicios de estadísticas (P3/P4/P5) y métricas (P6) ya existentes.

## Contexto Técnico

**Lenguaje/Versión**: Python 3 (backend), JavaScript Vanilla (frontend)

**Dependencias principales**: FastAPI, `fpdf2` (generación PDF — ya presente en
`backend/requirements.txt`), `minio`, `pandas`, `pyarrow`

**Almacenamiento**: MinIO. Bucket de aplicación `diabcare-app`, prefijo
`reportes/` (el bucket ya se usa para `modelos/`). Datos analíticos en
`diabetes-data` (stage Parquet).

**Pruebas**: pytest en `pruebas/api/` (contrato y flujo del módulo)

**Plataforma objetivo**: Servidor con Uvicorn (`backend/Principal.py`)

**Tipo de proyecto**: Aplicación web (backend FastAPI + frontend Vanilla)

**Metas de desempeño**: generación de un reporte estándar < 2 min (RNF-O-P07-004).
Nota: la generación de PDF es una operación on-demand, no un endpoint público de
alto tráfico, por lo que la meta P95 < 200 ms aplica a `GET /api/reportes/`
(listado) y a la descarga, no a la generación.

**Restricciones**: PDF en español; sin identificadores de paciente; acceso solo
`administrador` y `medico`.

**Alcance**: módulo P7 únicamente (3 endpoints + servicio + página frontend).

## Constitution Check

Referencia: `specs/000-sistema-general/constitution.md` (DiabCare Analytics v1.1.0)

| Principio | Pregunta de la puerta | Resultado |
|-----------|------------------------|-----------|
| I. SDD | ¿Expone/cambia API pública? | Sí. Contrato OpenAPI en `contracts/reportes-api.yaml` antes de implementar. **PASA** |
| II. Paquete-First | ¿Qué paquete? | P7. Rutas `backend/paquetes/reportes/`, `backend/paquetes/reportes/`, `frontend/paginas/clinico/reportes/`. **PASA** |
| III. Integridad DWH | ¿Lee/escribe datos clínicos? | Lee agregados del DWH vía servicios existentes; no omite ELT. **PASA** |
| IV. Test-First | ¿Qué pruebas? | pytest en `pruebas/api/test_reportes.py` (contrato + flujo). **PASA** |
| V. Seguridad | ¿Auth/clínico? | JWT + rol (`require_modulo('reportes')`); auditoría de generación/descarga; sin datos sensibles en PDF/logs. **PASA** |
| VI. Trazabilidad | ¿OE→OT→OO/depto/paquete/CU? | OE4→OT4.2→OO5.5.1/OO5.6.1, Operaciones Clínicas, P7. **PASA** |
| Desempeño | ¿Latencia/ELT/ML? | Generación < 2 min; listado/descarga < 200 ms. Excepción documentada para la generación. **PASA** |

**Resultado**: PASA — sin violaciones que requieran justificación en Complejidad.

## Estructura del Proyecto

### Documentación (este paquete)

```text
specs/003-operativo/paquetes/P07-reportes/
├── spec.md              # Especificación del paquete
├── plan.md              # Este archivo
├── research.md          # Decisiones técnicas (Fase 0)
├── data-model.md        # Entidades (Fase 1)
├── quickstart.md        # Guía de validación (Fase 1)
├── contracts/
│   └── reportes-api.yaml  # Contrato OpenAPI 3.0 (Fase 1)
└── tasks.md             # Generado por /speckit-tasks
```

### Código fuente (rutas reales del repositorio)

```text
backend/
├── paquetes/reportes/ReportesRutas.py
└── paquetes/reportes/ReportesServicio.py

frontend/
└── paginas/clinico/reportes/index.html

pruebas/
└── api/test_reportes.py
```

**Decisión de estructura**: Arquitectura por Paquetes (Principio II) en
`backend/paquetes/{nombre}/` y `frontend/paginas/{departamento}/{nombre}/`.

## Fase 0 — Investigación

Ver `research.md`. Resumen de decisiones:

1. Librería PDF: **fpdf2** (ya en `requirements.txt`); se descarta reportlab.
2. Persistencia: MinIO `diabcare-app/reportes/reporte_{timestamp}.pdf`.
3. Fuentes de datos: reutilizar `estadisticas_endpoint.estadisticas()` (P3),
   `obtener_metricas()` (P6) y filtros de `RegistrosClinicosServicio`.

## Fase 1 — Diseño y Contratos

- Entidades en `data-model.md` (Reporte, SecciónEstadísticas, SecciónMétricas,
  ResumenFiltrado).
- Contrato OpenAPI 3.0 en `contracts/reportes-api.yaml` (3 endpoints).
- Guía de validación en `quickstart.md`.
- Actualización del contexto del agente (`.cursor/rules/specify-rules.mdc`).

## Seguimiento de Complejidad

Sin violaciones a la constitución. No se requieren justificaciones de
complejidad. Única nota: la generación de PDF puede exceder 200 ms; se acepta por
ser operación on-demand y no un endpoint de lectura de alto tráfico.
