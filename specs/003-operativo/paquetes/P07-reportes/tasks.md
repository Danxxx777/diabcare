# Tareas: P7 — Reportes PDF

**Entrada**: Documentos de diseño en `specs/003-operativo/paquetes/P07-reportes/`

**Prerrequisitos**: `plan.md` (requerido), `spec.md` (requerido),
`research.md`, `data-model.md`, `contracts/reportes-api.yaml`, `quickstart.md`

**Pruebas**: incluidas (Principio IV de la constitución — Test-First).

**Organización**: por historia de usuario, para implementación y prueba
independientes.

## Formato: `[ID] [P?] [Historia] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Historia]**: US1–US4 (mapea a las capacidades de la spec)

## Historias de usuario

- **US1 (P1, MVP)**: Generar reporte PDF con estadísticas del dataset.
- **US2 (P2)**: Incluir métricas del modelo ML en el reporte.
- **US3 (P3)**: Incluir resumen de registros filtrados.
- **US4 (P4)**: Listar y descargar reportes previos.

---

## Fase 1: Setup (infraestructura compartida)

- [X] T001 Verificar que `fpdf2` está en `backend/requirements.txt` e instalarlo en el entorno (`pip install -r backend/requirements.txt`).
- [X] T002 [P] Confirmar acceso al bucket MinIO `diabcare-app` y crear el prefijo `reportes/` si no existe, reutilizando `servicios/configuracion/ConfiguracionClienteMinio.get_cliente()`.

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Debe completarse antes de las historias de usuario.**

- [X] T003 Crear el esqueleto del servicio en `backend/servicios/reportes/ReportesServicio.py` con la estructura: helpers de acceso a MinIO (subir/listar/descargar PDF) y firma de `generar_pdf(filtros, usuario)`.
- [X] T004 Definir en `backend/api/reportes/ReportesRutas.py` los 3 endpoints del contrato (`POST /api/reportes/generar`, `GET /api/reportes/`, `GET /api/reportes/{nombre}`) protegidos con `Depends(require_modulo('reportes'))`, devolviendo aún respuestas vacías/placeholder.
- [X] T005 [P] Añadir helper de auditoría en el servicio para registrar generación/descarga. Nota: el módulo `backend/servicios/auditoria/` está vacío (P11 no implementado), por lo que la auditoría se registra vía `logging` estándar (`AUDIT reporte_generado` / `AUDIT reporte_descargado`) sin inventar dependencias.

**Checkpoint**: rutas registradas y accesibles con control de rol; base lista.

---

## Fase 3: US1 — Generar reporte con estadísticas del dataset (P1) 🎯 MVP

**Objetivo**: producir un PDF descargable con estadísticas del dataset.

**Prueba independiente**: generar un reporte sin filtros y verificar que el PDF
contiene la sección de estadísticas y es descargable.

### Pruebas (escribir primero)

- [X] T006 [P] [US1] Crear `pruebas/api/test_reportes.py` con prueba de `POST /api/reportes/generar` (200 y respuesta con `nombre`) usando token de médico/administrador.

### Implementación

- [X] T007 [US1] Implementar en `ReportesServicio.py` la obtención de estadísticas reutilizando `servicios/registros_clinicos/estadisticas_endpoint.estadisticas()` y/o `GET /api/dataset/estadisticas`.
- [X] T008 [US1] Implementar `generar_pdf()` con `fpdf2`: encabezado institucional, fecha/hora, usuario, y sección "Estadísticas del dataset" (total, % diabetes, promedios BMI/HbA1c/glucosa, distribución por género) en `ReportesServicio.py`.
- [X] T009 [US1] Implementar la subida del PDF a MinIO `diabcare-app/reportes/reporte_{timestamp}.pdf` y conectar `POST /api/reportes/generar` para devolver `{nombre, ruta, fecha, tamano_mb}` en `ReportesRutas.py`.
- [X] T010 [US1] Registrar evento de auditoría en la generación (RF-O-P07-007).

**Checkpoint**: US1 funcional — se genera y persiste un PDF con estadísticas.

---

## Fase 4: US2 — Métricas del modelo ML (P2)

**Objetivo**: añadir al PDF la sección de métricas del modelo.

**Prueba independiente**: con modelo entrenado, el PDF incluye exactitud y
métricas; sin modelo, indica "no disponible".

### Pruebas

- [X] T011 [P] [US2] Añadir prueba en `pruebas/api/test_reportes.py` que verifique la sección de métricas (con y sin modelo entrenado).

### Implementación

- [X] T012 [US2] Obtener métricas con `servicios/prediccion/PrediccionServicio.obtener_metricas()` y agregar la sección "Métricas del modelo" al PDF en `ReportesServicio.py`; si hay error, escribir "Métricas del modelo no disponibles" (RF-O-P07-003).

**Checkpoint**: US1 + US2 funcionando juntas.

---

## Fase 5: US3 — Resumen de registros filtrados (P3)

**Objetivo**: aceptar filtros y reflejar el subconjunto en el PDF.

**Prueba independiente**: aplicar un filtro conocido y verificar que el conteo
del PDF coincide con la vista de registros.

### Pruebas

- [X] T013 [P] [US3] Añadir prueba de generación con filtros (incluido caso sin resultados → aviso) en `pruebas/api/test_reportes.py`.

### Implementación

- [X] T014 [US3] Validar filtros (`age_max ≥ age_min`, etc.) y devolver 400 ante combinaciones inválidas en `ReportesRutas.py` (modelo Pydantic `FiltroReporte`).
- [X] T015 [US3] Obtener el subconjunto y agregar la sección "Resumen de registros filtrados" (cantidad, distribución por diagnóstico/género, promedios) en `ReportesServicio.py`; si vacío, escribir "Sin registros para los filtros aplicados" (RN-O-P07-002). Nota: se reaplican los mismos filtros que `RegistrosClinicosServicio.buscar()` sobre `_extraer()` completo para que los agregados sean exactos (no solo los primeros 100).
- [X] T016 [US3] Garantizar que la sección solo incluye agregados (sin `encounter_id` ni filas), conforme a RNF-O-P07-002.

**Checkpoint**: US1 + US2 + US3 — reporte completo con sus tres secciones.

---

## Fase 6: US4 — Listar y descargar reportes (P4)

**Objetivo**: historial consultable y descarga directa.

**Prueba independiente**: generar un reporte, listarlo y descargarlo sin
regenerarlo.

### Pruebas

- [X] T017 [P] [US4] Añadir pruebas de `GET /api/reportes/` (listado) y `GET /api/reportes/{nombre}` (descarga 200 PDF, 404 inexistente) en `pruebas/api/test_reportes.py`.

### Implementación

- [X] T018 [US4] Implementar listado en `ReportesServicio.py` (nombre, fecha, tamaño) leyendo objetos de `diabcare-app/reportes/` y exponerlo en `GET /api/reportes/`.
- [X] T019 [US4] Implementar descarga en `GET /api/reportes/{nombre}` devolviendo el PDF como respuesta `application/pdf`; registrar auditoría de descarga; 404 si no existe.

**Checkpoint**: las cuatro historias funcionan de forma independiente.

---

## Fase 7: Frontend e integración

- [X] T020 [US1] Reemplazar el stub de `frontend/paginas/reportes/index.html` por la UI: botón "Generar reporte", formulario de filtros opcionales y tabla de reportes con botón de descarga por fila.
- [X] T021 [US4] Conectar la UI a los 3 endpoints (con token JWT en `Authorization`) y manejar estados (cargando, error, sin permiso).

---

## Fase 8: Pulido y validación

- [X] T022 [P] Ejecutar la guía `quickstart.md` y confirmar criterios CA-O-P07-001..004. **Hecho** (stack en vivo: MinIO vía docker + `uvicorn Principal:app`): login → `POST /generar` (con y sin filtros) → `GET /` (listado) → `GET /{nombre}` (descarga `application/pdf`, cabecera `%PDF-`) → 401 sin token. Nota: el volumen MinIO estaba vacío, por lo que las secciones de dataset/modelo muestran "no disponible"; para un video representativo, cargar primero el dataset (pipeline/generador) y entrenar el modelo.
- [X] T023 [P] Verificar que ningún PDF contiene identificadores de paciente (privacidad). Cubierto por la prueba automatizada `test_pdf_no_incluye_encounter_id` y por construcción del PDF (solo agregados).
- [X] T024 Ejecutar `pytest pruebas/api/test_reportes.py` y dejar la suite en verde. **Hecho**: 13/13 pruebas en verde (`cd backend && py -m pytest ../pruebas/api/test_reportes.py -q`).

---

## Dependencias y orden de ejecución

- **Setup (F1)** → **Fundacional (F2)** → **US1 (F3)** → US2/US3/US4.
- US2, US3 y US4 dependen de la base de generación (US1) pero son
  independientes entre sí una vez que US1 existe.
- **Frontend (F7)** depende de que existan los endpoints (F3–F6).
- **Pulido (F8)** al final.

## Oportunidades de paralelismo

- T002 con T001; T005 con T003/T004.
- Las pruebas marcadas [P] (T006, T011, T013, T017) pueden escribirse en
  paralelo por ser el mismo objetivo en archivo de pruebas con secciones
  distintas (coordinar para evitar choques en el mismo archivo).

## Estrategia MVP

1. Completar F1 + F2 + F3 (US1) → reporte con estadísticas: **MVP demostrable**.
2. Añadir US2 (métricas) → reporte clínico completo.
3. Añadir US3 (filtros) y US4 (historial) → módulo completo.

## Resumen

- **Total de tareas**: 24
- **Por historia**: US1=5 (T006–T010), US2=2 (T011–T012), US3=4 (T013–T016),
  US4=3 (T017–T019); Setup=2, Fundacional=3, Frontend=2, Pulido=3.
- **MVP**: US1 (Fases 1–3).
