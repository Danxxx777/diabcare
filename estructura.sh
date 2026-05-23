#!/bin/bash
# DiabCare Analytics - Estructura completa del proyecto

# === BACKEND ===
mkdir -p backend/api
mkdir -p backend/services
mkdir -p backend/models
mkdir -p backend/db
mkdir -p backend/utils
mkdir -p backend/scripts

# === FRONTEND ===
mkdir -p frontend/pages
mkdir -p frontend/estaticos/css
mkdir -p frontend/estaticos/js
mkdir -p frontend/estaticos/img
mkdir -p frontend/plantillas
mkdir -p frontend/componentes

# === ML ===
mkdir -p ml/modelos
mkdir -p ml/notebooks
mkdir -p ml/evaluacion
mkdir -p ml/datos_entrenamiento

# === DAGS (Airflow) ===
mkdir -p dags/scripts

# === STAGE (Parquet temporal) ===
mkdir -p stage

# === MINIO (estructura de buckets documentada) ===
mkdir -p minio/diabetes-data/stage
mkdir -p minio/diabetes-data/sinteticos
mkdir -p minio/diabetes-data/processed
mkdir -p minio/diabcare-app/modelos
mkdir -p minio/diabcare-app/reportes
mkdir -p minio/diabcare-app/exports

# === DOCS ===
mkdir -p docs/diagramas
mkdir -p docs/casos_de_uso
mkdir -p docs/entregables
mkdir -p docs/bd

# === PRUEBAS ===
mkdir -p pruebas/api
mkdir -p pruebas/ml
mkdir -p pruebas/integracion

# === CONFIG ===
mkdir -p config

# === LOGS ===
mkdir -p logs

# === PLUGINS (Airflow) ===
mkdir -p plugins

echo "✅ Estructura creada"
