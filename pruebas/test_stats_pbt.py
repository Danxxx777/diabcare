"""
test_stats_pbt.py — Pruebas basadas en propiedades para /api/stats.

Feature: diabcare-analytics
"""

import pytest
from unittest.mock import patch, MagicMock, call
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from main import app, TABLAS_PERMITIDAS

client = TestClient(app)

TABLAS_LISTA = sorted(TABLAS_PERMITIDAS)  # orden determinista para los tests


def _make_conn_with_failures(fail_set: set):
    """
    Crea un mock de get_conn() donde las tablas en `fail_set` lanzan excepción
    y las demás retornan un conteo aleatorio positivo.
    """
    conn = MagicMock()

    call_count = [0]

    def cursor_side_effect():
        cur = MagicMock()
        return cur

    conn.cursor.side_effect = cursor_side_effect

    # Parchar execute para que falle en las tablas de fail_set
    executed_tables = []

    original_cursor = conn.cursor

    def patched_cursor():
        cur = MagicMock()

        def execute_side_effect(sql, *args):
            # Extraer nombre de tabla del SQL "SELECT COUNT(*) FROM {tabla}"
            tabla = sql.strip().split()[-1]
            if tabla in fail_set:
                raise Exception(f"Simulated failure for table {tabla}")
            cur._last_tabla = tabla

        cur.execute.side_effect = execute_side_effect
        cur.fetchone.return_value = (42,)
        return cur

    conn.cursor.side_effect = patched_cursor
    return conn


# ── Property 6: Stats siempre retorna 11 claves con valores >= 0 ──────────────
# Feature: diabcare-analytics, Property 6: stats siempre retorna las 11 claves con valores no negativos

@given(
    st.frozensets(
        st.sampled_from(TABLAS_LISTA),
        max_size=len(TABLAS_LISTA),
    )
)
@settings(max_examples=50)
def test_stats_siempre_retorna_11_claves(fail_set):
    """
    Para cualquier subconjunto de tablas que fallen,
    GET /api/stats debe retornar exactamente 11 claves con valores enteros >= 0.
    """
    mock_conn = _make_conn_with_failures(fail_set)
    with patch("main.get_conn", return_value=mock_conn):
        response = client.get("/api/stats")

    assert response.status_code == 200
    data = response.json()

    # Siempre debe tener exactamente 11 claves
    assert len(data) == 11, f"Se esperaban 11 claves, se obtuvieron {len(data)}: {list(data.keys())}"

    # Cada clave debe ser una tabla de la whitelist
    assert set(data.keys()) == TABLAS_PERMITIDAS

    # Todos los valores deben ser enteros >= 0
    for tabla, conteo in data.items():
        assert isinstance(conteo, int), f"El conteo de '{tabla}' no es entero: {conteo!r}"
        assert conteo >= 0, f"El conteo de '{tabla}' es negativo: {conteo}"


def test_stats_con_conexion_fallida():
    """
    Si get_conn() lanza excepción, /api/stats debe retornar 11 claves con valor 0.
    """
    with patch("main.get_conn", side_effect=Exception("No se puede conectar")):
        response = client.get("/api/stats")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 11
    for tabla, conteo in data.items():
        assert conteo == 0, f"Se esperaba 0 para '{tabla}', se obtuvo {conteo}"
