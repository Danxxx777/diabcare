# Investigación Técnica (Fase 0): P7 — Reportes PDF

**Fecha**: 2026-06-19

Todas las decisiones se basan en código y dependencias reales del repositorio;
no se introducen tecnologías nuevas fuera del stack aprobado.

## Decisión 1: Librería de generación de PDF

- **Decisión**: usar **fpdf2**.
- **Justificación**: `fpdf2` ya está declarada en `backend/requirements.txt`
  (línea 8). No requiere añadir dependencias ni cambiar la constitución.
- **Alternativas consideradas**:
  - *reportlab*: la mencionaba una nota antigua (`.kiro`), pero NO está en
    `requirements.txt`; añadirla sería una dependencia nueva innecesaria.
  - *WeasyPrint/HTML→PDF*: requiere dependencias del sistema (GTK), descartada
    por complejidad de despliegue.

## Decisión 2: Persistencia de los reportes

- **Decisión**: guardar en MinIO, bucket `diabcare-app`, prefijo
  `reportes/reporte_{timestamp}.pdf`.
- **Justificación**: el bucket `diabcare-app` ya existe y se usa para modelos
  (`modelos/modelo_diabetes.pkl`, ver `PrediccionServicio.py`). El cliente MinIO
  se obtiene con `get_cliente()` de
  `paquetes/configuracion/ConfiguracionClienteMinio.py`.
- **Alternativas consideradas**:
  - Disco local: descartado; rompe la portabilidad y el modelo de
    almacenamiento del proyecto (Principio III).

## Decisión 3: Fuentes de datos del reporte

- **Decisión**: reutilizar servicios existentes, sin duplicar lógica:
  - Estadísticas clínicas: `paquetes/registros_clinicos/RegistrosClinicosServicio.estadisticas()`.
  - Estadísticas de dataset: `GET /api/dataset/estadisticas`
    (`DatasetRutas.estadisticas_dataset`).
  - Métricas del modelo: `paquetes/prediccion/PrediccionServicio.obtener_metricas()`
    (accuracy, precision, recall, f1, registros).
  - Filtros: `paquetes/registros_clinicos/RegistrosClinicosServicio.buscar()`.
- **Justificación**: cumple Integridad del DWH (III) y evita lógica redundante;
  los datos provienen del mismo origen que la UI.
- **Alternativas consideradas**:
  - Recalcular agregados dentro del servicio de reportes: descartado por
    duplicación y riesgo de divergencia con la vista de análisis (CA-O-P07-002).

## Decisión 4: Control de acceso

- **Decisión**: proteger los endpoints con `Depends(require_modulo('reportes'))`.
- **Justificación**: `PERMISOS_MODULOS["reportes"] = ["administrador", "medico"]`
  ya está definido en `nucleo/utilidades/Dependencias.py`. Reutiliza el mecanismo
  estándar del proyecto (Principio V).

## Decisión 5: Privacidad del contenido

- **Decisión**: el PDF solo incluye agregados (conteos, promedios,
  distribuciones); nunca `encounter_id`, ni filas individuales.
- **Justificación**: RNF-O-P07-002 y Principio V (HIPAA/GDPR). Se evita
  reidentificación.

## Decisión 6: Auditoría

- **Decisión**: registrar evento de auditoría en generación y descarga usando
  `paquetes/auditoria/AuditoriaServicio.registrar()`.
- **Justificación**: RF-O-P07-007 y Principio V.
- **Nota**: el módulo de auditoría está parcial (sin API REST); se usará su
  servicio/registrador internamente, sin depender de endpoints.

## Riesgos y mitigaciones

- *Dataset vacío*: el reporte se genera con secciones en cero y avisos (manejo de
  bordes ya soportado por los endpoints de estadísticas).
- *Modelo no entrenado*: la sección de métricas indica "no disponible" sin
  bloquear el resto (RF-O-P07-003).
- *Tamaño del PDF*: solo agregados → tamaño acotado; sin riesgo de memoria.
