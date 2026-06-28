# Especificación de Paquete: P6 — Predicción ML

**Nivel**: Operativo · **Departamento**: Operaciones Clínicas · **Paquete**: P6

**Casos de uso operativos**: CU-O08 (Predecir riesgo) y CU-O09 (Métricas ML) · OO5.6.1

**Estado**: Implementado

**Creado**: 2026-06-19

**Rutas reales**: `backend/api/prediccion/PrediccionRutas.py`,
`backend/servicios/prediccion/PrediccionServicio.py`,
`ml/modelos/entrenar.py`, `ml/modelos/predecir.py`, `ml/evaluacion/metricas.py`,
`frontend/paginas/prediccion/index.html`

## 1. Objetivo

Predecir el riesgo de diabetes de un paciente a partir de variables clínicas y
exponer las métricas de desempeño del modelo.

## 2. Contexto

Implementa el objetivo OO5.6.1 (predicción con RandomForest). Es el caso de uso
estrella del bloque clínico y la base de la ventaja competitiva (OE4).

## 3. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Médico | `medico` | Ejecutar predicciones, ver métricas |
| Administrador | `administrador` | Acceso total, entrenar |

Acceso: `PERMISOS_MODULOS["prediccion"] = ["administrador", "medico"]`.

## 4. Requisitos funcionales

- **RF-O-P06-001** (CU-O08): El sistema DEBE predecir el riesgo de diabetes a
  partir de age, bmi, hbA1c_level, blood_glucose_level, hypertension,
  heart_disease, devolviendo el diagnóstico estimado y probabilidad.
  *Real*: `POST /api/prediccion`.
- **RF-O-P06-002** (CU-O09): El sistema DEBE exponer las métricas del modelo.
  *Real*: `GET /api/prediccion/metricas`.
- **RF-O-P06-003**: El sistema DEBE permitir entrenar el modelo.
  *Real*: `POST /api/prediccion/entrenar`.
- **RF-O-P06-004**: El sistema DEBE informar si el modelo está disponible.
  *Real*: `GET /api/prediccion/estado`.

## 5. Requisitos no funcionales

- **RNF-O-P06-001**: El acceso exige rol `medico` o `administrador`.
- **RNF-O-P06-002**: El modelo de diabetes DEBE mantener una exactitud objetivo
  ≥ 96% sobre el conjunto de prueba validado (meta TA06).

## 6. Reglas de negocio

- **RN-O-P06-001**: La predicción requiere un modelo entrenado; si no existe, el
  sistema indica que debe entrenarse (`GET /estado`).
- **RN-O-P06-002**: Las métricas reportadas corresponden a la evaluación vigente
  del modelo.

## 7. Entradas

- Predicción: age, bmi, hbA1c_level, blood_glucose_level, hypertension (0/1),
  heart_disease (0/1).

## 8. Salidas

- Resultado de predicción (diagnóstico estimado + probabilidad).
- Métricas del modelo (exactitud y métricas de clasificación).
- Estado del modelo (disponible/no entrenado).

## 9. Escenarios

### Escenario 1: Predicción con modelo entrenado
- **Dado** un modelo disponible,
- **Cuando** se envían variables clínicas válidas,
- **Entonces** el sistema devuelve diagnóstico estimado y probabilidad.

### Escenario 2: Sin modelo entrenado
- **Dado** que no hay modelo entrenado,
- **Cuando** se consulta el estado,
- **Entonces** el sistema indica que debe entrenarse antes de predecir.

## 10. Criterios de aceptación

- **CA-O-P06-001**: Con modelo entrenado, la predicción devuelve probabilidad.
- **CA-O-P06-002**: Las métricas reflejan la evaluación vigente del modelo.
- **CA-O-P06-003**: Un rol sin permiso recibe 403.

## 11. Dependencias

- P1 (sesión y rol), P4 (dataset de entrenamiento), P8 (datos en el DWH).

## 12. Restricciones y fuera de alcance

- Fuera de alcance: reentrenamiento automático programado (MLOps) y predicción de
  churn de negocio (CU-O16), que pertenece a Crecimiento e Integraciones.
