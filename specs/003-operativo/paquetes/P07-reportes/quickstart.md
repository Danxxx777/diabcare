# Guía de Validación (quickstart): P7 — Reportes PDF

**Fecha**: 2026-06-19

Valida que el módulo de Reportes funciona de extremo a extremo. Referencia de
contrato: `contracts/reportes-api.yaml`. Modelo: `data-model.md`.

## Prerrequisitos

1. MinIO en ejecución (`docker-compose.yaml`) y accesible en `localhost:9000`.
2. Backend en marcha: desde `backend/`, `uvicorn Principal:app --reload --port 8000`.
3. Datos cargados (generar dataset si es necesario:
   `POST /api/dataset/generar`).
4. Modelo entrenado para la sección de métricas (opcional):
   `POST /api/prediccion/entrenar`.
5. Token JWT de un usuario `administrador` o `medico` (vía
   `POST /api/auth/login`).

## Escenario 1 — Generar reporte sin filtros (CA-O-P07-001)

```
POST /api/reportes/generar
Authorization: Bearer <token>
Content-Type: application/json
{}
```

Esperado: 200 con `{ nombre, ruta, fecha, tamano_mb }`. El PDF incluye las tres
secciones (estadísticas, métricas o aviso, resumen sin filtros).

## Escenario 2 — Listar reportes (CA-O-P07-004)

```
GET /api/reportes/
Authorization: Bearer <token>
```

Esperado: 200 con `reportes: [...]` incluyendo el reporte recién generado.

## Escenario 3 — Descargar reporte

```
GET /api/reportes/reporte_AAAAMMDD_HHMMSS.pdf
Authorization: Bearer <token>
```

Esperado: 200 con `Content-Type: application/pdf` y archivo legible.

## Escenario 4 — Filtros sin resultados (RN-O-P07-002)

```
POST /api/reportes/generar
Authorization: Bearer <token>
{ "year": 1900 }
```

Esperado: 200; el PDF contiene "Sin registros para los filtros aplicados" en la
sección de resumen filtrado.

## Escenario 5 — Acceso denegado (CA-O-P07-003 / seguridad)

```
POST /api/reportes/generar
Authorization: Bearer <token-de-analista>
```

Esperado: 403.

## Verificación de privacidad

Abrir el PDF generado y confirmar que NO aparece ningún `encounter_id` ni filas
individuales de pacientes; solo agregados (RNF-O-P07-002).

## Pruebas automatizadas

`pruebas/api/test_reportes.py` debe cubrir: generación 200, listado, descarga,
filtros sin resultados, y 401/403. (Se detalla en `tasks.md`.)
