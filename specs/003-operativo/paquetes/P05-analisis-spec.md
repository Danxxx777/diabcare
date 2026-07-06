# Especificación de Paquete: P5 — Análisis y Visualización

**Nivel**: Operativo · **Departamento**: Operaciones Clínicas · **Paquete**: P5

**Caso de uso operativo**: CU-O07 (Consultar estadísticas clínicas con Chart.js) · OO5.5.1

**Estado**: Implementado (vía endpoints de estadísticas de P3 y P4)

**Creado**: 2026-06-19

**Rutas reales**: estadísticas servidas por
`backend/paquetes/registros_clinicos/RegistrosClinicosRutas.py`
(`GET /api/registros/estadisticas`, lógica en
`backend/paquetes/registros_clinicos/estadisticas_endpoint.py`) y
`backend/paquetes/dataset/DatasetRutas.py` (`GET /api/dataset/estadisticas`).
Frontend: `frontend/paginas/clinico/analisis/index.html`,
`frontend/paginas/clinico/analisis/estadisticas/index.html`,
`frontend/estaticos/scripts/Estadisticas.js`, `Graficas.js`.

## 1. Objetivo

Presentar estadísticas clínicas (prevalencia, promedios, distribuciones,
comorbilidades, tendencias) de forma visual con gráficas para apoyar el análisis.

## 2. Contexto

P5 no expone un router propio; consume los endpoints de estadísticas de P3 y P4 y
los visualiza en el frontend con Chart.js. Es la capa analítica del bloque
clínico.

## 3. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Médico | `medico` | Consultar dashboards y gráficas |
| Administrador | `administrador` | Acceso total |

Acceso: `PERMISOS_MODULOS["analisis"] = ["administrador", "medico"]`.

## 4. Requisitos funcionales

- **RF-O-P05-001** (CU-O07): El sistema DEBE calcular estadísticas clínicas:
  totales, distribución por género, tabaquismo vs diabetes, raza, rangos de edad,
  promedios clínicos (BMI, HbA1c, glucosa), comorbilidades y top de ubicaciones.
  *Real*: `GET /api/registros/estadisticas` (ver `estadisticas_endpoint.py`).
- **RF-O-P05-002**: El sistema DEBE exponer estadísticas agregadas del dataset.
  *Real*: `GET /api/dataset/estadisticas`.
- **RF-O-P05-003**: El frontend DEBE visualizar las estadísticas con gráficas.
  *Real*: `frontend/paginas/clinico/analisis`, `clinico/analisis/estadisticas` + Chart.js.

## 5. Requisitos no funcionales

- **RNF-O-P05-001**: El acceso exige rol `medico` o `administrador`.
- **RNF-O-P05-002**: Las gráficas DEBEN reflejar datos reales del DWH.

## 6. Reglas de negocio

- **RN-O-P05-001**: HbA1c promedio > 7.5 se considera señal de alerta clínica.
- **RN-O-P05-002**: Los promedios se calculan separando casos con y sin diabetes.

## 7. Entradas

- Token de sesión. (Las estadísticas se calculan sobre el DWH completo.)

## 8. Salidas

- Objetos JSON con agregados para alimentar las gráficas (género, edad, raza,
  comorbilidades, promedios, top ubicaciones, tendencia por año).

## 9. Escenarios

### Escenario 1: Ver estadísticas clínicas
- **Dado** un médico autenticado y datos cargados,
- **Cuando** abre el módulo de análisis,
- **Entonces** ve las gráficas con prevalencia, promedios y distribuciones
  reales.

### Escenario 2: Dataset vacío
- **Dado** que no hay datos cargados,
- **Cuando** consulta estadísticas,
- **Entonces** el sistema responde con totales en cero sin error.

## 10. Criterios de aceptación

- **CA-O-P05-001**: Las gráficas muestran los valores agregados del DWH.
- **CA-O-P05-002**: Con dataset vacío, la respuesta es consistente (ceros).
- **CA-O-P05-003**: Un rol sin permiso recibe 403.

## 11. Dependencias

- P1 (sesión y rol), P3 (registros) y P4 (dataset) como fuente de datos.

## 12. Restricciones y fuera de alcance

- Fuera de alcance: dashboards configurables por el usuario y exportación directa
  de gráficas (la exportación a PDF la cubre P7).
