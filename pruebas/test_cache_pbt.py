"""
test_cache_pbt.py — Pruebas basadas en propiedades para la caché del dataset
y las funciones de tablas virtuales.

Feature: diabcare-analytics
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from hypothesis import given, settings, strategies as st
from fastapi.testclient import TestClient

from servidor import (
    app,
    generar_dim_paciente,
    generar_dim_ubicacion,
    generar_dim_raza,
    generar_dim_condicion,
    generar_fact_diabetes,
)
from configuracion_tests import crear_df_prueba

cliente = TestClient(app)


# ── Property 4: get_df es idempotente con caché activa ────────────────────────
# Feature: diabcare-analytics, Property 4: get_df es idempotente con caché activa

@settings(max_examples=20)
@given(st.integers(min_value=10, max_value=200))
def test_cache_idempotente(n_filas):
    """
    Con la caché ya poblada, obtener_dataset() debe retornar el mismo
    DataFrame sin realizar ninguna descarga adicional desde MinIO.
    """
    import servidor
    df_original = crear_df_prueba(n_filas)
    servidor._df_cache = df_original
    try:
        df1 = servidor.obtener_dataset()
        df2 = servidor.obtener_dataset()
        # Misma referencia en memoria (no se descargó de nuevo)
        assert df1 is df2
        assert len(df1) == n_filas
    finally:
        servidor._df_cache = None


# ── Property 5: Tablas virtuales son deterministas ────────────────────────────
# Feature: diabcare-analytics, Property 5: tablas virtuales son deterministas

FUNCIONES_VIRTUALES = [
    ("dim_paciente",  generar_dim_paciente),
    ("dim_ubicacion", generar_dim_ubicacion),
    ("dim_raza",      generar_dim_raza),
    ("dim_condicion", generar_dim_condicion),
    ("fact_diabetes", generar_fact_diabetes),
]


@given(st.integers(min_value=10, max_value=500))
@settings(max_examples=50)
def test_tablas_virtuales_deterministas(n_filas):
    """
    Para cualquier DataFrame de entrada, invocar cada función de tabla virtual
    dos veces debe producir DataFrames con el mismo número de filas y columnas.
    """
    df = crear_df_prueba(n_filas)
    for nombre, funcion in FUNCIONES_VIRTUALES:
        resultado1 = funcion(df)
        resultado2 = funcion(df)
        assert len(resultado1) == len(resultado2), (
            f"{nombre}: primera invocación retornó {len(resultado1)} filas, "
            f"segunda retornó {len(resultado2)}"
        )
        assert list(resultado1.columns) == list(resultado2.columns), (
            f"{nombre}: columnas inconsistentes entre invocaciones"
        )


@given(st.integers(min_value=10, max_value=500))
@settings(max_examples=50)
def test_fact_diabetes_misma_longitud_que_dataset(n_filas):
    """
    generar_fact_diabetes debe retornar exactamente n_filas filas
    (una por cada registro del dataset).
    """
    df = crear_df_prueba(n_filas)
    resultado = generar_fact_diabetes(df)
    assert len(resultado) == n_filas


@given(st.integers(min_value=10, max_value=500))
@settings(max_examples=50)
def test_dimensiones_sin_duplicados(n_filas):
    """
    Las dimensiones (dim_paciente, dim_ubicacion, dim_raza, dim_condicion)
    no deben tener filas duplicadas en sus columnas de negocio.
    """
    df = crear_df_prueba(n_filas)

    for nombre, funcion in FUNCIONES_VIRTUALES[:-1]:  # Excluir fact_diabetes
        resultado = funcion(df)
        id_col = f"id_{nombre.replace('dim_', '')}"
        columnas_negocio = [c for c in resultado.columns if c != id_col]
        if columnas_negocio:
            sin_duplicados = resultado[columnas_negocio].drop_duplicates()
            assert len(resultado) == len(sin_duplicados), (
                f"{nombre}: tiene {len(resultado) - len(sin_duplicados)} filas duplicadas"
            )
