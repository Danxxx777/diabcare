"""
conftest.py — Fixtures compartidos para los tests de DiabCare Analytics.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

import sys
import os

# Asegurar que el directorio raíz del proyecto esté en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app


@pytest.fixture
def client():
    """TestClient de FastAPI para pruebas de endpoints."""
    return TestClient(app)


@pytest.fixture
def mock_conn():
    """
    Mock de pg8000 connection + cursor.
    Uso:
        with patch("main.get_conn", return_value=mock_conn):
            ...
    """
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn


def make_cursor_with_rows(rows, col_names=None, count=None):
    """
    Crea un cursor mock que retorna `rows` en fetchall() y `count` en fetchone().
    `col_names` se usa para simular cursor.description.
    """
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cur.fetchone.return_value = (count if count is not None else len(rows),)
    if col_names:
        cur.description = [(c,) for c in col_names]
    return cur
