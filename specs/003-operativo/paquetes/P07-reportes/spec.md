# Especificación de Paquete: P7 — Reportes

**Nivel**: Operativo · **Departamento**: Operaciones Clínicas · **Paquete**: P7

**Caso de uso operativo**: Reportes clínicos (deriva de OO5.5.1 / OO5.6.1)

**Estado**: No implementado (router y servicio stub; `ReportesServicio.py` vacío)

**Creado**: 2026-06-19

**Rutas previstas**: `backend/api/reportes/ReportesRutas.py`,
`backend/servicios/reportes/ReportesServicio.py`,
`frontend/paginas/reportes/index.html`

## 1. Objetivo

Permitir generar reportes clínicos descargables en PDF que resuman estadísticas
del dataset, métricas del modelo de predicción y un resumen de registros
filtrados, para compartir hallazgos fuera de la plataforma.

## 2. Contexto

El paquete P7 es el único del bloque clínico operativo que aún no está
implementado. Reutiliza las estadísticas ya disponibles (P3, P4, P5) y las
métricas del modelo (P6). Es el módulo objetivo prioritario para completar el
sistema operativo de GA07.

## 3. Actores

| Actor | Rol | Acceso |
|-------|-----|--------|
| Médico | `medico` | Generar y descargar reportes |
| Administrador | `administrador` | Generar y descargar reportes |

Acceso según `PERMISOS_MODULOS["reportes"] = ["administrador", "medico"]`
(verificado en `backend/utilidades/Dependencias.py`).

## 4. Requisitos funcionales

- **RF-O-P07-001**: El sistema DEBE permitir a un usuario autorizado generar un
  reporte clínico en PDF.
- **RF-O-P07-002**: El reporte DEBE incluir estadísticas del dataset (total de
  registros, % con diabetes, promedios de BMI, HbA1c y glucosa, distribución por
  género).
- **RF-O-P07-003**: El reporte DEBE incluir métricas del modelo de predicción
  cuando exista evaluación vigente; si no, indicar que no están disponibles.
- **RF-O-P07-004**: El sistema DEBE aceptar filtros opcionales (año, ubicación,
  diabetes, género, rango de edad) y reflejar el subconjunto en un resumen.
- **RF-O-P07-005**: El sistema DEBE entregar el PDF en español, con fecha/hora de
  generación y usuario solicitante.
- **RF-O-P07-006**: El sistema DEBE listar los reportes generados (nombre, fecha,
  tamaño) y permitir su descarga posterior.
- **RF-O-P07-007**: El sistema DEBE registrar en auditoría cada generación y
  descarga de reporte.

## 5. Requisitos no funcionales

- **RNF-O-P07-001** (Seguridad): la generación y descarga exigen JWT y rol
  permitido.
- **RNF-O-P07-002** (Privacidad): el PDF NO DEBE incluir identificadores de
  paciente ni datos que permitan reidentificación; solo agregados.
- **RNF-O-P07-003** (Idioma): el contenido del PDF DEBE estar en español.
- **RNF-O-P07-004** (Desempeño): la generación de un reporte estándar DEBE
  completarse en menos de 2 minutos de cara al usuario.

## 6. Reglas de negocio

- **RN-O-P07-001**: Solo `administrador` y `medico` acceden al módulo.
- **RN-O-P07-002**: Si los filtros no devuelven registros, el reporte se genera
  con un aviso explícito de "sin registros para los filtros aplicados".
- **RN-O-P07-003**: Los datos del reporte provienen del DWH (MinIO/Parquet).

## 7. Entradas

- Filtros opcionales: año, ubicación, diabetes (0/1), género, rango de edad.
- Identidad del usuario (token JWT).

## 8. Salidas

- Archivo PDF descargable.
- Listado de reportes disponibles (nombre, fecha, tamaño).
- Mensajes de validación/error.

## 9. Escenarios

### Escenario 1: Generar reporte sin filtros
- **Dado** un usuario autorizado y datos disponibles,
- **Cuando** solicita generar un reporte,
- **Entonces** el sistema produce un PDF con estadísticas del dataset y métricas
  ML, y lo ofrece para descarga.

### Escenario 2: Generar reporte con filtros sin resultados
- **Dado** un usuario autorizado,
- **Cuando** genera un reporte con filtros que no devuelven registros,
- **Entonces** el PDF se genera con el aviso "sin registros para los filtros
  aplicados".

### Escenario 3: Acceso denegado
- **Dado** un usuario con rol `analista`,
- **Cuando** intenta generar un reporte,
- **Entonces** el sistema responde 403.

## 10. Criterios de aceptación

- **CA-O-P07-001**: Un usuario autorizado genera y descarga un PDF con las tres
  secciones (estadísticas, métricas ML o aviso, resumen filtrado o sin filtros).
- **CA-O-P07-002**: Los conteos del resumen filtrado coinciden con la vista de
  registros para los mismos filtros.
- **CA-O-P07-003**: El PDF no contiene identificadores de paciente.
- **CA-O-P07-004**: Un reporte previo puede descargarse desde el listado sin
  regenerarlo.

## 11. Dependencias

- P1 (sesión y roles), P3 (registros), P4 (dataset/estadísticas), P5 (análisis),
  P6 (métricas del modelo).
- Almacenamiento MinIO para persistir los PDF.

## 12. Restricciones y fuera de alcance

- Restricción: el contenido se compone de agregados; nunca datos individuales
  identificables.
- Fuera de alcance: envío automático por correo, programación de reportes
  recurrentes y plantillas personalizables por usuario (versión futura).

## 13. Artefactos de diseño

- Plan de implementación: `plan.md`
- Investigación técnica: `research.md`
- Modelo de datos: `data-model.md`
- Contrato de API: `contracts/reportes-api.yaml`
- Guía de validación: `quickstart.md`
- Tareas: `tasks.md` (se genera con `/speckit-tasks`)
