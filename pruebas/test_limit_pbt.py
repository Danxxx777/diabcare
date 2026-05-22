"""
test_limit_pbt.py — Pruebas basadas en propiedades para el parámetro limit.

Feature: diabcare-analytics
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from main import app, TABLAS_PERMITIDAS

client = TestClient(app)

# Tabla fija para las pruebas de limit
TABLA_TEST = "raza"


def _mock_conn_for_limit(limit_value):
    """Mock que devuelve exactamente `limit_value` filas."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    rows = [{"id_raza": i, "nombre": f"raza_{i}", "codigo": f"R{i}"} for i in range(limit_value)]
    cur.fetchall.return_value = rows
    cur.fetchone.return_value = (100000,)  # total simulado
    cur.description = [("id_raza",), ("nombre",), ("codigo",)]
    return conn


# ── Property 3 (rango válido): len(rows) <= limit y total >= len(rows) ────────
# Feature: diabcare-analytics, Property 3: contrato del parámetro limit (rango válido)

@given(st.integers(min_value=1, max_value=500))
@settings(max_examples=100)
def test_limit_valido_contrato(limit):
    """
    Para cualquier limit en [1, 500], el endpoint debe retornar HTTP 200
    y len(rows) <= limit y total >= len(rows).
    """
    mock_conn = _mock_conn_for_limit(limit)
    with patch("main.get_conn", return_value=mock_conn):
        response = client.get(f"/api/tabla/{TABLA_TEST}?limit={limit}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["rows"]) <= limit
    assert data["total"] >= len(data["rows"])


# ── Property 3 (rango inválido): debe retornar HTTP 422 ──────────────────────
# Feature: diabcare-analytics, Property 3: contrato del parámetro limit (rango inválido)

@given(st.integers().filter(lambda x: x < 1 or x > 500))
@settings(max_examples=100)
def test_limit_invalido_retorna_422(limit):
    """
    Para cualquier limit fuera de [1, 500], el endpoint debe retornar HTTP 422.
    """
    response = client.get(f"/api/tabla/{TABLA_TEST}?limit={limit}")
    assert response.status_code == 422
