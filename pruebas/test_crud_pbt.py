"""
test_crud_pbt.py — Pruebas basadas en propiedades para el CRUD de fact_diabetes.

Feature: diabcare-analytics
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from servidor import app
from configuracion_tests import crear_df_prueba

cliente = TestClient(app)


def inyectar_cache(df):
    import servidor
    servidor._df_cache = df


def limpiar_cache():
    import servidor
    servidor._df_cache = None


# ── Property 10: CRUD respeta los límites del índice ──────────────────────────
# Feature: diabcare-analytics, Property 10: CRUD respeta los límites del índice

@given(
    n_filas=st.integers(min_value=1, max_value=50),
    id_fact=st.integers(min_value=-100, max_value=-1),
)
@settings(max_examples=50)
def test_crud_indice_negativo_retorna_404(n_filas, id_fact):
    """
    GET, PUT y DELETE con id_fact negativo deben retornar HTTP 404.
    """
    df = crear_df_prueba(n_filas)
    inyectar_cache(df)
    try:
        assert cliente.get(f"/api/fact/{id_fact}").status_code == 404
        assert cliente.put(f"/api/fact/{id_fact}?bmi=25.0").status_code == 404
        assert cliente.delete(f"/api/fact/{id_fact}").status_code == 404
    finally:
        limpiar_cache()


@given(n_filas=st.integers(min_value=1, max_value=50))
@settings(max_examples=50)
def test_crud_indice_igual_a_longitud_retorna_404(n_filas):
    """
    GET, PUT y DELETE con id_fact == len(df) deben retornar HTTP 404.
    """
    df = crear_df_prueba(n_filas)
    inyectar_cache(df)
    try:
        id_fuera = n_filas  # índice exactamente igual al tamaño
        assert cliente.get(f"/api/fact/{id_fuera}").status_code == 404
        assert cliente.put(f"/api/fact/{id_fuera}?bmi=25.0").status_code == 404
        assert cliente.delete(f"/api/fact/{id_fuera}").status_code == 404
    finally:
        limpiar_cache()


# ── Property 11: DELETE reindexea correctamente ───────────────────────────────
# Feature: diabcare-analytics, Property 11: DELETE reindexea correctamente

@given(n_filas=st.integers(min_value=2, max_value=50))
@settings(max_examples=50)
def test_delete_reduce_conteo_y_reindexea(n_filas):
    """
    Tras DELETE /api/fact/0:
    - registros_restantes == n_filas - 1
    - Los índices del DataFrame resultante son contiguos desde 0.
    """
    import servidor
    df = crear_df_prueba(n_filas)
    inyectar_cache(df)
    try:
        respuesta = cliente.delete("/api/fact/0")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["ok"] is True
        assert datos["registros_restantes"] == n_filas - 1

        # Verificar que los índices son contiguos desde 0
        df_resultante = servidor._df_cache
        assert list(df_resultante.index) == list(range(n_filas - 1))
    finally:
        limpiar_cache()


@given(
    n_filas=st.integers(min_value=1, max_value=50),
    nuevo_bmi=st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=50)
def test_put_actualiza_valor_en_cache(n_filas, nuevo_bmi):
    """
    PUT /api/fact/0?bmi=X debe actualizar el valor de bmi en la caché.
    """
    import servidor
    df = crear_df_prueba(n_filas)
    inyectar_cache(df)
    try:
        respuesta = cliente.put(f"/api/fact/0?bmi={nuevo_bmi}")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["ok"] is True
        assert abs(datos["registro"]["bmi"] - nuevo_bmi) < 0.001
        # Verificar que la caché también fue actualizada
        assert abs(servidor._df_cache.at[0, "bmi"] - nuevo_bmi) < 0.001
    finally:
        limpiar_cache()
