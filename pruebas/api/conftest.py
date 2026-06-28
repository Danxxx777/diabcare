"""
Fixtures compartidos para las pruebas de API de los módulos del avance GA07.
"""

import os
import sys

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


@pytest.fixture
def cliente_api():
    """TestClient sobre Principal:app, con cwd en backend para los StaticFiles."""
    from fastapi.testclient import TestClient
    cwd = os.getcwd()
    os.chdir(BACKEND)
    try:
        try:
            from Principal import app
        except Exception as e:  # entorno sin static dirs / dependencias
            pytest.skip(f"No se pudo importar Principal:app: {e}")
        yield TestClient(app)
    finally:
        os.chdir(cwd)


def payload_admin():
    return {"payload": {"sub": "1", "rol": "administrador", "correo": "admin@diabcare.com"}}


def payload_analista():
    return {"payload": {"sub": "2", "rol": "analista", "correo": "analista@diabcare.com"}}


def payload_medico():
    return {"payload": {"sub": "3", "rol": "medico", "correo": "medico@diabcare.com"}}
