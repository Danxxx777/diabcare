"""
test_empresa_pbt.py — Pruebas basadas en propiedades para /api/empresa.

Feature: diabcare-analytics
"""

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from main import app

client = TestClient(app)

CAMPOS_REQUERIDOS = {
    "nombre", "slogan", "mision", "vision",
    "objetivos_estrategicos", "objetivos_tacticos", "objetivos_operacionales",
    "problemas_sistemas", "problemas_decisiones",
}


# ── Property 7: Empresa tiene estructura y cardinalidad fijas ─────────────────
# Feature: diabcare-analytics, Property 7: respuesta de empresa tiene estructura y cardinalidad fijas

@given(st.none())  # Estrategia trivial: la respuesta es estática
@settings(max_examples=1)
def test_empresa_estructura_y_cardinalidad(_):
    """
    GET /api/empresa debe retornar exactamente los 9 campos requeridos,
    con los arrays de objetivos de longitud 3 y los de problemas de longitud 10.
    """
    response = client.get("/api/empresa")
    assert response.status_code == 200
    data = response.json()

    # Exactamente 9 campos
    assert set(data.keys()) == CAMPOS_REQUERIDOS, (
        f"Campos inesperados: {set(data.keys()) - CAMPOS_REQUERIDOS} | "
        f"Campos faltantes: {CAMPOS_REQUERIDOS - set(data.keys())}"
    )

    # Arrays de objetivos: longitud exactamente 3
    for campo in ("objetivos_estrategicos", "objetivos_tacticos", "objetivos_operacionales"):
        assert isinstance(data[campo], list), f"'{campo}' no es una lista"
        assert len(data[campo]) == 3, f"'{campo}' tiene {len(data[campo])} elementos, se esperaban 3"

    # Arrays de problemas: longitud exactamente 10
    for campo in ("problemas_sistemas", "problemas_decisiones"):
        assert isinstance(data[campo], list), f"'{campo}' no es una lista"
        assert len(data[campo]) == 10, f"'{campo}' tiene {len(data[campo])} elementos, se esperaban 10"

    # Campos de texto no vacíos
    for campo in ("nombre", "slogan", "mision", "vision"):
        assert isinstance(data[campo], str) and len(data[campo]) > 0, (
            f"'{campo}' debe ser un string no vacío"
        )
