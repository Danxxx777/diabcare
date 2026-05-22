"""
test_stats_servidor_pbt.py — Pruebas basadas en propiedades para /api/stats.

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

CLAVES_ESPERADAS = {
    "diabetes_dataset", "dim_paciente", "dim_ubicacion",
    "dim_raza", "dim_condicion", "fact_diabetes",
    "total_con_diabetes", "total_sin_diabetes",
}


def inyectar_cache(df):
    import servidor
    servidor._df_cache = df


def limpiar_cache():
    import servidor
    servidor._df_cache = None


# ── Property 6: Stats siempre retorna 8 claves con valores >= 0 ───────────────
# Feature: diabcare-analytics, Property 6: stats siempre retorna las 8 claves con valores no negativos

@given(st.integers(min_value=0, max_value=1000))
@settings(max_examples=50)
def test_stats_siempre_retorna_8_claves(n_filas):
    """
    Para cualquier tamaño de dataset (incluyendo 0 filas),
    GET /api/stats debe retornar exactamente 8 claves con valores enteros >= 0.
    """
    df = crear_df_prueba(n_filas) if n_filas > 0 else crear_df_prueba(1).iloc[0:0]
    inyectar_cache(df)
    try:
        respuesta = cliente.get("/api/stats")
        assert respuesta.status_code == 200
        datos = respuesta.json()

        assert len(datos) == 8, f"Se esperaban 8 claves, se obtuvieron {len(datos)}: {list(datos.keys())}"
        assert set(datos.keys()) == CLAVES_ESPERADAS

        for clave, valor in datos.items():
            assert isinstance(valor, int), f"El valor de '{clave}' no es entero: {valor!r}"
            assert valor >= 0, f"El valor de '{clave}' es negativo: {valor}"
    finally:
        limpiar_cache()


@given(st.integers(min_value=1, max_value=500))
@settings(max_examples=50)
def test_stats_total_con_sin_diabetes_suma_dataset(n_filas):
    """
    total_con_diabetes + total_sin_diabetes debe ser igual a diabetes_dataset.
    """
    df = crear_df_prueba(n_filas)
    inyectar_cache(df)
    try:
        respuesta = cliente.get("/api/stats")
        datos = respuesta.json()
        assert datos["total_con_diabetes"] + datos["total_sin_diabetes"] == datos["diabetes_dataset"]
    finally:
        limpiar_cache()
