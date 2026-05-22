"""
test_charts_pbt.py — Pruebas basadas en propiedades para los endpoints de charts.

Feature: diabcare-analytics
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from main import app

client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _conn_diabetes_por_anio(rows):
    """Mock que retorna `rows` para /api/chart/diabetes-por-anio."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = rows
    return conn


def _conn_pacientes_por_ubicacion(rows):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = rows
    return conn


def _conn_tratamientos(rows):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = rows
    return conn


# ── Property 8: Estructura de respuestas de charts ───────────────────────────
# Feature: diabcare-analytics, Property 8: estructura de respuestas de charts

@given(
    st.lists(
        st.tuples(
            st.integers(min_value=2000, max_value=2030),  # anio
            st.integers(min_value=0, max_value=50000),    # con_diabetes
            st.integers(min_value=0, max_value=50000),    # sin_diabetes
        ),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=50)
def test_diabetes_por_anio_estructura(rows_data):
    """
    Cada elemento de /api/chart/diabetes-por-anio debe tener
    los campos 'anio', 'con_diabetes' y 'sin_diabetes'.
    """
    # Ordenar por anio ASC para simular lo que hace la BD
    rows_sorted = sorted(rows_data, key=lambda r: r[0])
    mock_conn = _conn_diabetes_por_anio(rows_sorted)
    with patch("main.get_conn", return_value=mock_conn):
        response = client.get("/api/chart/diabetes-por-anio")
    assert response.status_code == 200
    data = response.json()
    for item in data:
        assert "anio" in item
        assert "con_diabetes" in item
        assert "sin_diabetes" in item


@given(
    st.lists(
        st.tuples(
            st.text(min_size=1, max_size=30),  # ubicacion
            st.integers(min_value=1, max_value=100000),  # total
        ),
        min_size=1,
        max_size=15,
    )
)
@settings(max_examples=50)
def test_pacientes_por_ubicacion_estructura(rows_data):
    """
    Cada elemento de /api/chart/pacientes-por-ubicacion debe tener
    los campos 'ubicacion' y 'total', y la lista debe tener <= 15 elementos.
    """
    mock_conn = _conn_pacientes_por_ubicacion(rows_data)
    with patch("main.get_conn", return_value=mock_conn):
        response = client.get("/api/chart/pacientes-por-ubicacion")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 15
    for item in data:
        assert "ubicacion" in item
        assert "total" in item


@given(
    st.lists(
        st.tuples(
            st.text(min_size=1, max_size=30),  # nivel
            st.integers(min_value=1, max_value=100000),  # total
        ),
        min_size=1,
        max_size=5,
    )
)
@settings(max_examples=50)
def test_tratamientos_estructura(rows_data):
    """
    Cada elemento de /api/chart/tratamientos debe tener los campos 'nivel' y 'total'.
    """
    mock_conn = _conn_tratamientos(rows_data)
    with patch("main.get_conn", return_value=mock_conn):
        response = client.get("/api/chart/tratamientos")
    assert response.status_code == 200
    data = response.json()
    for item in data:
        assert "nivel" in item
        assert "total" in item


# ── Property 9: Ordenamiento de charts es consistente ────────────────────────
# Feature: diabcare-analytics, Property 9: ordenamiento de charts es consistente

@given(
    st.lists(
        st.tuples(
            st.integers(min_value=2000, max_value=2030),
            st.integers(min_value=0, max_value=50000),
            st.integers(min_value=0, max_value=50000),
        ),
        min_size=2,
        max_size=20,
        unique_by=lambda t: t[0],  # años únicos
    )
)
@settings(max_examples=50)
def test_diabetes_por_anio_orden_ascendente(rows_data):
    """
    /api/chart/diabetes-por-anio debe retornar los objetos en orden
    ascendente por 'anio'.
    """
    rows_sorted = sorted(rows_data, key=lambda r: r[0])
    mock_conn = _conn_diabetes_por_anio(rows_sorted)
    with patch("main.get_conn", return_value=mock_conn):
        response = client.get("/api/chart/diabetes-por-anio")
    assert response.status_code == 200
    data = response.json()
    anios = [item["anio"] for item in data]
    assert anios == sorted(anios), f"No está ordenado ascendentemente: {anios}"


@given(
    st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),
            st.integers(min_value=1, max_value=100000),
        ),
        min_size=2,
        max_size=15,
    )
)
@settings(max_examples=50)
def test_pacientes_por_ubicacion_orden_descendente(rows_data):
    """
    /api/chart/pacientes-por-ubicacion debe retornar los objetos en orden
    descendente por 'total'.
    """
    rows_sorted = sorted(rows_data, key=lambda r: r[1], reverse=True)
    mock_conn = _conn_pacientes_por_ubicacion(rows_sorted)
    with patch("main.get_conn", return_value=mock_conn):
        response = client.get("/api/chart/pacientes-por-ubicacion")
    assert response.status_code == 200
    data = response.json()
    totales = [item["total"] for item in data]
    assert totales == sorted(totales, reverse=True), (
        f"No está ordenado descendentemente: {totales}"
    )


@given(
    st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),
            st.integers(min_value=1, max_value=100000),
        ),
        min_size=2,
        max_size=5,
    )
)
@settings(max_examples=50)
def test_tratamientos_orden_descendente(rows_data):
    """
    /api/chart/tratamientos debe retornar los objetos en orden
    descendente por 'total'.
    """
    rows_sorted = sorted(rows_data, key=lambda r: r[1], reverse=True)
    mock_conn = _conn_tratamientos(rows_sorted)
    with patch("main.get_conn", return_value=mock_conn):
        response = client.get("/api/chart/tratamientos")
    assert response.status_code == 200
    data = response.json()
    totales = [item["total"] for item in data]
    assert totales == sorted(totales, reverse=True), (
        f"No está ordenado descendentemente: {totales}"
    )


# ── Property 10: Charts retornan lista vacía cuando no hay datos ──────────────
# Feature: diabcare-analytics, Property 10: charts retornan lista vacía cuando no hay datos

def _conn_vacio():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = []
    return conn


def test_diabetes_por_anio_vacio():
    """GET /api/chart/diabetes-por-anio retorna [] con HTTP 200 cuando no hay datos."""
    with patch("main.get_conn", return_value=_conn_vacio()):
        response = client.get("/api/chart/diabetes-por-anio")
    assert response.status_code == 200
    assert response.json() == []


def test_pacientes_por_ubicacion_vacio():
    """GET /api/chart/pacientes-por-ubicacion retorna [] con HTTP 200 cuando no hay datos."""
    with patch("main.get_conn", return_value=_conn_vacio()):
        response = client.get("/api/chart/pacientes-por-ubicacion")
    assert response.status_code == 200
    assert response.json() == []


def test_tratamientos_vacio():
    """GET /api/chart/tratamientos retorna [] con HTTP 200 cuando no hay datos."""
    with patch("main.get_conn", return_value=_conn_vacio()):
        response = client.get("/api/chart/tratamientos")
    assert response.status_code == 200
    assert response.json() == []
