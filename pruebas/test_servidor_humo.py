"""
test_servidor_humo.py — Smoke tests para DiabCare Analytics.

Verifican que los endpoints principales responden correctamente
con la caché mockeada (sin MinIO real).
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from fastapi.testclient import TestClient
from servidor import app, TABLAS_MAP
from configuracion_tests import crear_df_prueba

cliente = TestClient(app)


def inyectar_cache(df):
    import servidor
    servidor._df_cache = df


def limpiar_cache():
    import servidor
    servidor._df_cache = None


def test_pagina_principal_retorna_200():
    """GET / debe retornar HTTP 200 con contenido HTML."""
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert "DiabCare" in respuesta.text


def test_stats_retorna_200_con_8_claves():
    """GET /api/stats debe retornar HTTP 200 con exactamente 8 claves."""
    df = crear_df_prueba(50)
    inyectar_cache(df)
    try:
        respuesta = cliente.get("/api/stats")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        claves_esperadas = {
            "diabetes_dataset", "dim_paciente", "dim_ubicacion",
            "dim_raza", "dim_condicion", "fact_diabetes",
            "total_con_diabetes", "total_sin_diabetes",
        }
        assert set(datos.keys()) == claves_esperadas
        assert len(datos) == 8
    finally:
        limpiar_cache()


def test_empresa_retorna_200_con_7_campos():
    """GET /api/empresa debe retornar HTTP 200 con los 7 campos requeridos."""
    respuesta = cliente.get("/api/empresa")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    campos_requeridos = {
        "nombre", "slogan", "mision", "vision",
        "objetivos_estrategicos", "objetivos_tacticos", "objetivos_operacionales",
    }
    assert set(datos.keys()) == campos_requeridos


def test_tabla_no_permitida_retorna_400():
    """GET /api/tabla/tabla_inexistente debe retornar HTTP 400."""
    respuesta = cliente.get("/api/tabla/tabla_inexistente")
    assert respuesta.status_code == 400


def test_todas_las_tablas_del_mapa_retornan_200():
    """Cada tabla del TABLAS_MAP debe retornar HTTP 200."""
    df = crear_df_prueba(20)
    inyectar_cache(df)
    try:
        for tabla in TABLAS_MAP.keys():
            respuesta = cliente.get(f"/api/tabla/{tabla}?limit=5")
            assert respuesta.status_code == 200, f"Falló {tabla}: {respuesta.status_code}"
    finally:
        limpiar_cache()


def test_charts_retornan_200():
    """Los cuatro endpoints de chart deben retornar HTTP 200."""
    df = crear_df_prueba(50)
    inyectar_cache(df)
    try:
        endpoints = [
            "/api/chart/diabetes-por-anio",
            "/api/chart/pacientes-por-ubicacion",
            "/api/chart/distribucion-bmi",
            "/api/chart/glucosa-vs-diabetes",
        ]
        for endpoint in endpoints:
            respuesta = cliente.get(endpoint)
            assert respuesta.status_code == 200, f"Falló {endpoint}: {respuesta.status_code}"
    finally:
        limpiar_cache()


def test_cargar_dataset_invalida_cache():
    """POST /api/cargar-dataset con MinIO mockeado debe retornar ok=True."""
    from unittest.mock import MagicMock, patch
    from datetime import datetime, timezone

    objeto_mock = MagicMock()
    objeto_mock.object_name = "stage/datos.parquet"
    objeto_mock.last_modified = datetime(2024, 1, 1, tzinfo=timezone.utc)

    df_mock = crear_df_prueba(100)
    import io
    buffer = io.BytesIO()
    df_mock.to_parquet(buffer, index=False)
    buffer.seek(0)

    cliente_minio_mock = MagicMock()
    cliente_minio_mock.list_objects.return_value = [objeto_mock]
    cliente_minio_mock.get_object.return_value = buffer

    import servidor
    servidor._df_cache = None

    with patch("servidor.obtener_cliente_minio", return_value=cliente_minio_mock):
        respuesta = cliente.post("/api/cargar-dataset")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["ok"] is True
    assert datos["registros"] == 100
    assert isinstance(datos["columnas"], list)

    limpiar_cache()
