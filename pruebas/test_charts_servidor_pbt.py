"""
test_charts_servidor_pbt.py — Pruebas basadas en propiedades para los endpoints de charts.

Feature: diabcare-analytics
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st
import numpy as np
import pandas as pd

from servidor import app
from configuracion_tests import crear_df_prueba

cliente = TestClient(app)


def inyectar_cache(df):
    import servidor
    servidor._df_cache = df


def limpiar_cache():
    import servidor
    servidor._df_cache = None


# ── Property 8: Estructura de respuestas de charts ────────────────────────────
# Feature: diabcare-analytics, Property 8: estructura de respuestas de charts

@given(st.integers(min_value=10, max_value=200))
@settings(max_examples=50)
def test_diabetes_por_anio_estructura(n_filas):
    """
    Cada elemento de /api/chart/diabetes-por-anio debe tener
    los campos 'anio', 'con_diabetes' y 'sin_diabetes'.
    """
    df = crear_df_prueba(n_filas)
    inyectar_cache(df)
    try:
        respuesta = cliente.get("/api/chart/diabetes-por-anio")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        for item in datos:
            assert "anio" in item
            assert "con_diabetes" in item
            assert "sin_diabetes" in item
            assert item["con_diabetes"] >= 0
            assert item["sin_diabetes"] >= 0
    finally:
        limpiar_cache()


@given(st.integers(min_value=10, max_value=200))
@settings(max_examples=50)
def test_pacientes_por_ubicacion_estructura_y_limite(n_filas):
    """
    Cada elemento de /api/chart/pacientes-por-ubicacion debe tener
    los campos 'ubicacion' y 'total', y la lista debe tener <= 15 elementos.
    """
    df = crear_df_prueba(n_filas)
    inyectar_cache(df)
    try:
        respuesta = cliente.get("/api/chart/pacientes-por-ubicacion")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert len(datos) <= 15
        for item in datos:
            assert "ubicacion" in item
            assert "total" in item
            assert item["total"] > 0
    finally:
        limpiar_cache()


@given(st.integers(min_value=10, max_value=200))
@settings(max_examples=50)
def test_distribucion_bmi_tiene_6_categorias(n_filas):
    """
    /api/chart/distribucion-bmi debe retornar exactamente 6 categorías.
    """
    df = crear_df_prueba(n_filas)
    inyectar_cache(df)
    try:
        respuesta = cliente.get("/api/chart/distribucion-bmi")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert len(datos) == 6
        categorias = {item["categoria"] for item in datos}
        assert categorias == {"<18.5", "18.5-25", "25-30", "30-35", "35-40", ">40"}
    finally:
        limpiar_cache()


@given(st.integers(min_value=10, max_value=200))
@settings(max_examples=50)
def test_glucosa_vs_diabetes_tiene_2_grupos(n_filas):
    """
    /api/chart/glucosa-vs-diabetes debe retornar exactamente 2 grupos.
    """
    df = crear_df_prueba(n_filas)
    # Asegurar que hay registros de ambas clases
    df.loc[0, "diabetes"] = 0
    df.loc[1, "diabetes"] = 1
    inyectar_cache(df)
    try:
        respuesta = cliente.get("/api/chart/glucosa-vs-diabetes")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert len(datos) == 2
        grupos = {item["diabetes"] for item in datos}
        assert grupos == {"Con diabetes", "Sin diabetes"}
        for item in datos:
            assert "glucosa_promedio" in item
            assert item["glucosa_promedio"] > 0
    finally:
        limpiar_cache()


# ── Property 9: Ordenamiento de charts es consistente ────────────────────────
# Feature: diabcare-analytics, Property 9: ordenamiento de charts es consistente

@given(st.integers(min_value=20, max_value=200))
@settings(max_examples=50)
def test_diabetes_por_anio_orden_ascendente(n_filas):
    """
    /api/chart/diabetes-por-anio debe retornar los objetos en orden
    ascendente por 'anio'.
    """
    df = crear_df_prueba(n_filas)
    inyectar_cache(df)
    try:
        respuesta = cliente.get("/api/chart/diabetes-por-anio")
        datos = respuesta.json()
        if len(datos) >= 2:
            anios = [item["anio"] for item in datos]
            assert anios == sorted(anios), f"No está ordenado ascendentemente: {anios}"
    finally:
        limpiar_cache()


@given(st.integers(min_value=20, max_value=200))
@settings(max_examples=50)
def test_pacientes_por_ubicacion_orden_descendente(n_filas):
    """
    /api/chart/pacientes-por-ubicacion debe retornar los objetos en orden
    descendente por 'total'.
    """
    df = crear_df_prueba(n_filas)
    inyectar_cache(df)
    try:
        respuesta = cliente.get("/api/chart/pacientes-por-ubicacion")
        datos = respuesta.json()
        if len(datos) >= 2:
            totales = [item["total"] for item in datos]
            assert totales == sorted(totales, reverse=True), (
                f"No está ordenado descendentemente: {totales}"
            )
    finally:
        limpiar_cache()
