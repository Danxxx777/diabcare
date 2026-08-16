# -*- coding: utf-8 -*-
"""
Fixtures compartidas.

`test_hospital_api.py` pedía un fixture `client` que no existía en ningún lado,
así que esas siete pruebas nunca llegaron a ejecutarse. TestClient levanta la
app en proceso: no hace falta un servidor aparte, pero sí MinIO, porque los
datos viven ahí.
"""
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "api: prueba de extremo a extremo contra la app (necesita MinIO)"
    )


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from Principal import app

    # TestClient guarda las cookies entre llamadas, que es como autentica la app
    # desde que la sesión dejó de viajar en un JWT de localStorage.
    with TestClient(app) as c:
        yield c
