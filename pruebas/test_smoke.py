"""
test_smoke.py — Smoke tests para DiabCare Analytics.
Verifican que los endpoints principales responden correctamente sin BD real.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app, TABLAS_PERMITIDAS

client = TestClient(app)


def test_pagina_principal_retorna_200():
    """GET / debe retornar HTTP 200 con contenido HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "DiabCare" in response.text


def test_stats_retorna_200_con_11_claves():
    """GET /api/stats debe retornar HTTP 200 con exactamente 11 claves."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchone.return_value = (0,)
    with patch("main.get_conn", return_value=conn):
        response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 11
    assert set(data.keys()) == TABLAS_PERMITIDAS


def test_empresa_retorna_200_con_9_campos():
    """GET /api/empresa debe retornar HTTP 200 con los 9 campos requeridos."""
    response = client.get("/api/empresa")
    assert response.status_code == 200
    data = response.json()
    campos_requeridos = {
        "nombre", "slogan", "mision", "vision",
        "objetivos_estrategicos", "objetivos_tacticos", "objetivos_operacionales",
        "problemas_sistemas", "problemas_decisiones",
    }
    assert set(data.keys()) == campos_requeridos


def test_tabla_no_permitida_retorna_400():
    """GET /api/tabla/tabla_inexistente debe retornar HTTP 400."""
    response = client.get("/api/tabla/tabla_inexistente")
    assert response.status_code == 400


def test_charts_retornan_200():
    """Los tres endpoints de chart deben retornar HTTP 200."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = []
    with patch("main.get_conn", return_value=conn):
        for endpoint in [
            "/api/chart/diabetes-por-anio",
            "/api/chart/pacientes-por-ubicacion",
            "/api/chart/tratamientos",
        ]:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Falló {endpoint}: {response.status_code}"
