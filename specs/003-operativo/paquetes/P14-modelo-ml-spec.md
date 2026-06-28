# Especificación de Paquete: P14 — Gestión del Modelo ML

**Nivel**: Operativo · **Departamento**: Datos e Ingeniería · **Paquete**: P14

**Caso de uso operativo**: CU-O09 (Consultar métricas ML) · OO5.6.1 · TA06 §14-B

**Estado**: Implementado (entrega GA07)

**Rutas reales**: `backend/api/modelo_ml/ModeloMlRutas.py`,
`backend/servicios/modelo_ml/ModeloMlServicio.py`,
`frontend/paginas/modelo_ml/index.html`

## 1. Objetivo

Gestionar el ciclo de vida del modelo RandomForest de diabetes: información,
reentrenamiento desde Parquet y consulta de historial de entrenamientos.

## 2. Contexto

TA06 documenta RandomForest 96% accuracy sobre dataset clínico. P14 complementa
P6 (predicción en línea) con gestión explícita del artefacto en MinIO.

## 3. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Analista | `analista` | Ver info, reentrenar, historial |
| Administrador | `administrador` | Acceso total |

Acceso: `PERMISOS_MODULOS["modelo_ml"] = ["administrador", "analista"]`.

## 4. Requisitos funcionales

- **RF-O-P14-001** (CU-O09): Información del modelo (algoritmo, métricas, estado).
  *Real*: `GET /api/modelo-ml/info`.
- **RF-O-P14-002**: Reentrenar desde datos en stage/. *Real*: `POST /api/modelo-ml/reentrenar`.
- **RF-O-P14-003**: Historial de entrenamientos. *Real*: `GET /api/modelo-ml/historial`.

## 5. Requisitos no funcionales

- **RNF-O-P14-001**: Meta TA06 accuracy ≥ 96% sobre split de prueba documentado.
- **RNF-O-P14-002**: Modelo persistido en MinIO `diabcare-app/modelos/`.

## 6. Reglas de negocio

- **RN-O-P14-001**: Features: age, bmi, hbA1c_level, blood_glucose_level,
  hypertension, heart_disease (TA06 §14-B).

## 7–8. Entradas y salidas

- Reentrenar: token analista/admin → métricas accuracy, precision, recall, f1.
- Info: estado disponible/no entrenado + métricas vigentes.

## 9. Escenarios

### Escenario 1: Modelo entrenado
- **Cuando** consulta `/api/modelo-ml/info` → **Entonces** `disponible: true` y métricas.

### Escenario 2: Reentrenar
- **Cuando** POST reentrenar con dataset cargado → **Entonces** actualiza métricas y MinIO.

## 10. Criterios de aceptación

- **CA-O-P14-001**: Info refleja mismo modelo usado por P6 predicción.
- **CA-O-P14-002**: Reentrenar registra evento auditable.

## 11. Dependencias

- P4/P8 (datos Parquet), P6 (PrediccionServicio), P11.

## 12. Fuera de alcance

- MLOps automatizado cada 90 días (TA06 aprendizaje); churn XGBoost (CU-T10).
