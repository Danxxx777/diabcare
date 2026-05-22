"""
test_servidor_unitario.py — Tests unitarios para DiabCare Analytics.

Cubre:
- TABLAS_MAP: tablas permitidas y rechazadas
- Validación del parámetro limit
- Funciones de tablas virtuales (dim_paciente, dim_ubicacion, etc.)
- CRUD: límites de índice, actualización y eliminación
- MinIO: sin objetos, sin parquet
- Endpoint /api/empresa: cardinalidad y campos
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from servidor import (
    app,
    TABLAS_MAP,
    generar_dim_paciente,
    generar_dim_ubicacion,
    generar_dim_raza,
    generar_dim_condicion,
    generar_fact_diabetes,
)
from configuracion_tests import crear_df_prueba

cliente = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────

def inyectar_cache(df):
    """Inyecta un DataFrame en _df_cache para evitar llamadas a MinIO."""
    import servidor
    servidor._df_cache = df


def limpiar_cache():
    """Limpia _df_cache tras el test."""
    import servidor
    servidor._df_cache = None


# ── TABLAS_MAP: tablas permitidas retornan 200 ─────────────────────────────────

@pytest.mark.parametrize("tabla", sorted(TABLAS_MAP.keys()))
def test_tabla_permitida_retorna_200(tabla):
    """Cada tabla del TABLAS_MAP debe retornar HTTP 200."""
    df = crear_df_prueba(10)
    inyectar_cache(df)
    try:
        respuesta = cliente.get(f"/api/tabla/{tabla}")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert "rows" in datos
        assert "total" in datos
    finally:
        limpiar_cache()


# ── TABLAS_MAP: nombres no permitidos retornan 400 ────────────────────────────

@pytest.mark.parametrize("nombre", [
    "",
    "pg_tables",
    "users",
    "'; DROP TABLE paciente; --",
    "information_schema",
    "sys",
    "admin",
    "1; SELECT * FROM paciente",
    "diabetes_clinical",   # nombre del esquema anterior, ya no válido
    "paciente",            # tabla relacional anterior, ya no válida
])
def test_tabla_no_permitida_retorna_400(nombre):
    """Nombres fuera del TABLAS_MAP deben retornar HTTP 400."""
    respuesta = cliente.get(f"/api/tabla/{nombre}")
    assert respuesta.status_code == 400


# ── Validación del parámetro limit ────────────────────────────────────────────

@pytest.mark.parametrize("limit", [1, 50, 250, 500])
def test_limit_en_rango_retorna_200(limit):
    """Valores de limit en [1, 500] deben retornar HTTP 200."""
    df = crear_df_prueba(10)
    inyectar_cache(df)
    try:
        respuesta = cliente.get(f"/api/tabla/dim_raza?limit={limit}")
        assert respuesta.status_code == 200
    finally:
        limpiar_cache()


@pytest.mark.parametrize("limit", [0, 501, -1, 1000])
def test_limit_fuera_de_rango_retorna_422(limit):
    """Valores de limit fuera de [1, 500] deben retornar HTTP 422."""
    respuesta = cliente.get(f"/api/tabla/dim_raza?limit={limit}")
    assert respuesta.status_code == 422


# ── Funciones de tablas virtuales ─────────────────────────────────────────────

def test_dim_paciente_columnas():
    """generar_dim_paciente debe retornar un DataFrame con id_paciente, gender, age."""
    df = crear_df_prueba(50)
    resultado = generar_dim_paciente(df)
    assert "id_paciente" in resultado.columns
    assert "gender" in resultado.columns
    assert "age" in resultado.columns
    assert len(resultado) > 0


def test_dim_ubicacion_columnas():
    """generar_dim_ubicacion debe retornar un DataFrame con id_ubicacion, location, year."""
    df = crear_df_prueba(50)
    resultado = generar_dim_ubicacion(df)
    assert "id_ubicacion" in resultado.columns
    assert "location" in resultado.columns
    assert "year" in resultado.columns


def test_dim_raza_columnas():
    """generar_dim_raza debe retornar un DataFrame con id_raza y columnas de raza."""
    df = crear_df_prueba(50)
    resultado = generar_dim_raza(df)
    assert "id_raza" in resultado.columns
    assert len(resultado) > 0


def test_dim_condicion_columnas():
    """generar_dim_condicion debe retornar un DataFrame con id_condicion y condiciones."""
    df = crear_df_prueba(50)
    resultado = generar_dim_condicion(df)
    assert "id_condicion" in resultado.columns
    assert "hypertension" in resultado.columns
    assert "heart_disease" in resultado.columns


def test_fact_diabetes_columnas():
    """generar_fact_diabetes debe retornar un DataFrame con id_fact y métricas clínicas."""
    df = crear_df_prueba(50)
    resultado = generar_fact_diabetes(df)
    assert "id_fact" in resultado.columns
    assert "bmi" in resultado.columns
    assert "hbA1c_level" in resultado.columns
    assert "blood_glucose_level" in resultado.columns
    assert "diabetes" in resultado.columns


def test_dim_paciente_sin_duplicados():
    """generar_dim_paciente no debe tener filas duplicadas en (gender, age)."""
    df = crear_df_prueba(200)
    resultado = generar_dim_paciente(df)
    sin_duplicados = resultado.drop(columns=["id_paciente"]).drop_duplicates()
    assert len(resultado) == len(sin_duplicados)


def test_fact_diabetes_misma_cantidad_que_dataset():
    """generar_fact_diabetes debe tener el mismo número de filas que el dataset."""
    df = crear_df_prueba(100)
    resultado = generar_fact_diabetes(df)
    assert len(resultado) == len(df)


# ── CRUD: límites de índice ────────────────────────────────────────────────────

def test_leer_registro_valido():
    """GET /api/fact/0 debe retornar HTTP 200 con los campos del registro."""
    df = crear_df_prueba(10)
    inyectar_cache(df)
    try:
        respuesta = cliente.get("/api/fact/0")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert "bmi" in datos
        assert "diabetes" in datos
    finally:
        limpiar_cache()


@pytest.mark.parametrize("id_fact", [-1, -100])
def test_leer_registro_indice_negativo_retorna_404(id_fact):
    """GET /api/fact/{id} con índice negativo debe retornar HTTP 404."""
    df = crear_df_prueba(10)
    inyectar_cache(df)
    try:
        respuesta = cliente.get(f"/api/fact/{id_fact}")
        assert respuesta.status_code == 404
        assert respuesta.json()["detail"] == "Registro no encontrado"
    finally:
        limpiar_cache()


def test_leer_registro_fuera_de_rango_retorna_404():
    """GET /api/fact/N donde N >= len(df) debe retornar HTTP 404."""
    df = crear_df_prueba(10)
    inyectar_cache(df)
    try:
        respuesta = cliente.get(f"/api/fact/{len(df)}")
        assert respuesta.status_code == 404
    finally:
        limpiar_cache()


def test_actualizar_registro_bmi():
    """PUT /api/fact/0?bmi=99.9 debe actualizar el valor en la caché."""
    df = crear_df_prueba(10)
    inyectar_cache(df)
    try:
        respuesta = cliente.put("/api/fact/0?bmi=99.9")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["ok"] is True
        assert abs(datos["registro"]["bmi"] - 99.9) < 0.01
    finally:
        limpiar_cache()


def test_eliminar_registro_reduce_conteo():
    """DELETE /api/fact/0 debe reducir el conteo en 1 y reindexar."""
    df = crear_df_prueba(10)
    inyectar_cache(df)
    try:
        n_original = len(df)
        respuesta = cliente.delete("/api/fact/0")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["ok"] is True
        assert datos["registros_restantes"] == n_original - 1
    finally:
        limpiar_cache()


def test_eliminar_registro_fuera_de_rango_retorna_404():
    """DELETE /api/fact/N donde N >= len(df) debe retornar HTTP 404."""
    df = crear_df_prueba(5)
    inyectar_cache(df)
    try:
        respuesta = cliente.delete(f"/api/fact/{len(df)}")
        assert respuesta.status_code == 404
    finally:
        limpiar_cache()


# ── MinIO: errores de conexión ─────────────────────────────────────────────────

def test_minio_sin_objetos_retorna_404():
    """Si MinIO no tiene objetos en stage/, debe retornar HTTP 404."""
    import servidor
    servidor._df_cache = None
    cliente_mock = MagicMock()
    cliente_mock.list_objects.return_value = []
    with patch("servidor.obtener_cliente_minio", return_value=cliente_mock):
        respuesta = cliente.get("/api/stats")
    assert respuesta.status_code == 404
    assert "No hay archivos parquet" in respuesta.json()["detail"]


def test_minio_sin_parquet_retorna_404():
    """Si MinIO tiene objetos pero ninguno es .parquet, debe retornar HTTP 404."""
    import servidor
    servidor._df_cache = None
    objeto_mock = MagicMock()
    objeto_mock.object_name = "stage/datos.csv"
    objeto_mock.last_modified = None
    cliente_mock = MagicMock()
    cliente_mock.list_objects.return_value = [objeto_mock]
    with patch("servidor.obtener_cliente_minio", return_value=cliente_mock):
        respuesta = cliente.get("/api/stats")
    assert respuesta.status_code == 404
    assert "No se encontraron archivos .parquet" in respuesta.json()["detail"]


# ── /api/empresa: cardinalidad y campos ───────────────────────────────────────

def test_empresa_campos_requeridos():
    """GET /api/empresa debe retornar exactamente los 7 campos requeridos."""
    respuesta = cliente.get("/api/empresa")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    campos_esperados = {
        "nombre", "slogan", "mision", "vision",
        "objetivos_estrategicos", "objetivos_tacticos", "objetivos_operacionales",
    }
    assert set(datos.keys()) == campos_esperados


def test_empresa_cardinalidad_objetivos():
    """Los tres arrays de objetivos deben tener exactamente 3 elementos."""
    respuesta = cliente.get("/api/empresa")
    datos = respuesta.json()
    assert len(datos["objetivos_estrategicos"]) == 3
    assert len(datos["objetivos_tacticos"]) == 3
    assert len(datos["objetivos_operacionales"]) == 3
