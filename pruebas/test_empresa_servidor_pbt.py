"""
test_empresa_servidor_pbt.py — Pruebas basadas en propiedades para /api/empresa.

Feature: diabcare-analytics
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from servidor import app

cliente = TestClient(app)

CAMPOS_REQUERIDOS = {
    "nombre", "slogan", "mision", "vision",
    "objetivos_estrategicos", "objetivos_tacticos", "objetivos_operacionales",
}


# ── Property 7: Empresa tiene estructura y cardinalidad fijas ─────────────────
# Feature: diabcare-analytics, Property 7: respuesta de empresa tiene estructura y cardinalidad fijas

@given(st.none())  # Respuesta estática, una sola iteración es suficiente
@settings(max_examples=1)
def test_empresa_estructura_y_cardinalidad(_):
    """
    GET /api/empresa debe retornar exactamente los 7 campos requeridos,
    con los arrays de objetivos de longitud exactamente 3 cada uno.
    """
    respuesta = cliente.get("/api/empresa")
    assert respuesta.status_code == 200
    datos = respuesta.json()

    # Exactamente 7 campos
    assert set(datos.keys()) == CAMPOS_REQUERIDOS, (
        f"Campos inesperados: {set(datos.keys()) - CAMPOS_REQUERIDOS} | "
        f"Campos faltantes: {CAMPOS_REQUERIDOS - set(datos.keys())}"
    )

    # Arrays de objetivos: longitud exactamente 3
    for campo in ("objetivos_estrategicos", "objetivos_tacticos", "objetivos_operacionales"):
        assert isinstance(datos[campo], list), f"'{campo}' no es una lista"
        assert len(datos[campo]) == 3, (
            f"'{campo}' tiene {len(datos[campo])} elementos, se esperaban 3"
        )

    # Campos de texto no vacíos
    for campo in ("nombre", "slogan", "mision", "vision"):
        assert isinstance(datos[campo], str) and len(datos[campo]) > 0, (
            f"'{campo}' debe ser un string no vacío"
        )
