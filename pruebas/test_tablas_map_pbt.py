"""
test_tablas_map_pbt.py — Pruebas basadas en propiedades para el TABLAS_MAP.

Feature: diabcare-analytics
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from unittest.mock import patch
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from servidor import app, TABLAS_MAP
from configuracion_tests import crear_df_prueba

cliente = TestClient(app)


def inyectar_cache(df):
    import servidor
    servidor._df_cache = df


def limpiar_cache():
    import servidor
    servidor._df_cache = None


# ── Property 1: TABLAS_MAP rechaza tablas no autorizadas ──────────────────────
# Feature: diabcare-analytics, Property 1: TABLAS_MAP rechaza tablas no autorizadas

@given(st.text().filter(lambda s: s not in TABLAS_MAP))
@settings(max_examples=100)
def test_tablas_map_rechaza_no_autorizadas(nombre):
    """
    Para cualquier string que no pertenezca al TABLAS_MAP,
    GET /api/tabla/{nombre} debe retornar HTTP 400.
    No se debe generar ningún DataFrame.
    """
    respuesta = cliente.get(f"/api/tabla/{nombre}")
    assert respuesta.status_code == 400


# ── Property 2: TABLAS_MAP acepta todas las tablas autorizadas ────────────────
# Feature: diabcare-analytics, Property 2: TABLAS_MAP acepta todas las tablas autorizadas

@given(st.sampled_from(sorted(TABLAS_MAP.keys())))
@settings(max_examples=50)
def test_tablas_map_acepta_autorizadas(nombre):
    """
    Para cualquier nombre de tabla del TABLAS_MAP,
    GET /api/tabla/{nombre} debe retornar HTTP 200 con campos 'rows' y 'total'.
    """
    df = crear_df_prueba(20)
    inyectar_cache(df)
    try:
        respuesta = cliente.get(f"/api/tabla/{nombre}?limit=5")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert "rows" in datos
        assert "total" in datos
        assert isinstance(datos["total"], int)
        assert datos["total"] >= 0
    finally:
        limpiar_cache()
