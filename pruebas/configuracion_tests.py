"""
configuracion_tests.py — Fixtures compartidos para los tests de DiabCare Analytics.

Proporciona:
- cliente: TestClient de FastAPI para pruebas de endpoints.
- df_prueba: DataFrame de pandas con datos sintéticos para tests unitarios.
- mock_minio_vacio: Mock de MinIO sin archivos en stage/.
- mock_minio_sin_parquet: Mock de MinIO con archivos pero sin .parquet.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

import sys
import os

# Asegurar que el directorio app esté en el path para importar servidor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from servidor import app, TABLAS_MAP


@pytest.fixture
def cliente():
    """TestClient de FastAPI para pruebas de endpoints."""
    return TestClient(app)


def crear_df_prueba(n_filas: int = 100) -> pd.DataFrame:
    """
    Crea un DataFrame sintético con la misma estructura que el dataset real.
    Útil para mockear _df_cache en tests sin necesidad de MinIO.

    Args:
        n_filas: Número de filas a generar (default 100).

    Returns:
        DataFrame con columnas: gender, age, location, year, hypertension,
        heart_disease, smoking_history, bmi, hbA1c_level, blood_glucose_level,
        diabetes, race_AfricanAmerican, race_Asian, race_Caucasian,
        race_Hispanic, race_Other.
    """
    rng = np.random.default_rng(seed=42)
    return pd.DataFrame({
        "gender":              rng.choice(["Male", "Female"], size=n_filas),
        "age":                 rng.uniform(18, 90, size=n_filas).round(1),
        "location":            rng.choice(["California", "Texas", "Florida", "New York", "Ohio"], size=n_filas),
        "year":                rng.choice([2019, 2020, 2021, 2022], size=n_filas),
        "hypertension":        rng.integers(0, 2, size=n_filas),
        "heart_disease":       rng.integers(0, 2, size=n_filas),
        "smoking_history":     rng.choice(["never", "former", "current", "ever", "not current"], size=n_filas),
        "bmi":                 rng.uniform(15, 50, size=n_filas).round(1),
        "hbA1c_level":         rng.uniform(3.5, 14.0, size=n_filas).round(1),
        "blood_glucose_level": rng.integers(80, 400, size=n_filas),
        "diabetes":            rng.integers(0, 2, size=n_filas),
        "race_AfricanAmerican": rng.integers(0, 2, size=n_filas),
        "race_Asian":           rng.integers(0, 2, size=n_filas),
        "race_Caucasian":       rng.integers(0, 2, size=n_filas),
        "race_Hispanic":        rng.integers(0, 2, size=n_filas),
        "race_Other":           rng.integers(0, 2, size=n_filas),
    })


@pytest.fixture
def df_prueba():
    """DataFrame sintético de 100 filas para tests."""
    return crear_df_prueba(100)


@pytest.fixture
def mock_cache_poblada(df_prueba):
    """
    Fixture que inyecta df_prueba en _df_cache del servidor
    para que los endpoints no intenten conectarse a MinIO.
    """
    import servidor
    servidor._df_cache = df_prueba
    yield df_prueba
    servidor._df_cache = None  # Limpiar tras el test


@pytest.fixture
def mock_minio_vacio():
    """Mock de MinIO que retorna lista vacía de objetos (sin archivos en stage/)."""
    cliente_mock = MagicMock()
    cliente_mock.list_objects.return_value = []
    return cliente_mock


@pytest.fixture
def mock_minio_sin_parquet():
    """Mock de MinIO con objetos pero ninguno con extensión .parquet."""
    objeto_mock = MagicMock()
    objeto_mock.object_name = "stage/datos.csv"
    objeto_mock.last_modified = None
    cliente_mock = MagicMock()
    cliente_mock.list_objects.return_value = [objeto_mock]
    return cliente_mock
