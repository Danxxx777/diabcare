"""
test_whitelist_pbt.py — Pruebas basadas en propiedades para la whitelist de tablas.

Feature: diabcare-analytics
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from main import app, TABLAS_PERMITIDAS

client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_conn_with_rows(rows, col_names, total):
    """Devuelve un mock de get_conn() que simula una tabla con datos."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = rows
    cur.fetchone.return_value = (total,)
    cur.description = [(c,) for c in col_names]
    return conn


# ── Property 1: Whitelist rechaza tablas no autorizadas ───────────────────────
# Feature: diabcare-analytics, Property 1: whitelist rechaza tablas no autorizadas

@given(st.text().filter(lambda s: s not in TABLAS_PERMITIDAS))
@settings(max_examples=100)
def test_whitelist_rechaza_no_autorizadas(nombre):
    """
    Para cualquier string que no pertenezca a TABLAS_PERMITIDAS,
    GET /api/tabla/{nombre} debe retornar HTTP 400 con detail == "Tabla no permitida".
    No se debe ejecutar ninguna consulta a la BD.
    """
    response = client.get(f"/api/tabla/{nombre}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Tabla no permitida"


# ── Property 2: Whitelist acepta todas las tablas autorizadas ─────────────────
# Feature: diabcare-analytics, Property 2: whitelist acepta todas las tablas autorizadas

@given(st.sampled_from(sorted(TABLAS_PERMITIDAS)))
@settings(max_examples=100)
def test_whitelist_acepta_autorizadas(nombre):
    """
    Para cualquier nombre de tabla de la whitelist,
    GET /api/tabla/{nombre} debe retornar HTTP 200 con campos 'rows' y 'total'.
    """
    mock_conn = _mock_conn_with_rows(
        rows=[{"id": 1, "col": "val"}],
        col_names=["id", "col"],
        total=1,
    )
    with patch("main.get_conn", return_value=mock_conn):
        response = client.get(f"/api/tabla/{nombre}")
    assert response.status_code == 200
    data = response.json()
    assert "rows" in data
    assert "total" in data
