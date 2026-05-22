"""
test_unit.py — Tests unitarios para DiabCare Analytics.
Cubre whitelist, validación de limit, asignar_tratamiento, ETL timeout/error y empresa.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import subprocess

from main import app, TABLAS_PERMITIDAS

client = TestClient(app)

# Inicializar trat_map para tests
import load_data
load_data.trat_map.update({
    "Normal": 1,
    "Prediabetes": 2,
    "Diabetes leve": 3,
    "Diabetes moderada": 4,
    "Diabetes severa": 5,
})
from load_data import asignar_tratamiento, trat_map


# ── Whitelist: todas las tablas permitidas retornan 200 ───────────────────────

@pytest.mark.parametrize("tabla", sorted(TABLAS_PERMITIDAS))
def test_tabla_permitida_retorna_200(tabla):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = [{"id": 1}]
    cur.fetchone.return_value = (1,)
    cur.description = [("id",)]
    with patch("main.get_conn", return_value=conn):
        response = client.get(f"/api/tabla/{tabla}")
    assert response.status_code == 200


# ── Whitelist: nombres no permitidos retornan 400 ─────────────────────────────

@pytest.mark.parametrize("nombre", [
    "",
    "pg_tables",
    "users",
    "'; DROP TABLE paciente; --",
    "information_schema",
    "sys",
    "admin",
    "1; SELECT * FROM paciente",
])
def test_tabla_no_permitida_retorna_400(nombre):
    response = client.get(f"/api/tabla/{nombre}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Tabla no permitida"


# ── Validación de limit ───────────────────────────────────────────────────────

@pytest.mark.parametrize("limit", [1, 250, 500])
def test_limit_en_rango_retorna_200(limit):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = []
    cur.fetchone.return_value = (0,)
    cur.description = [("id",)]
    with patch("main.get_conn", return_value=conn):
        response = client.get(f"/api/tabla/raza?limit={limit}")
    assert response.status_code == 200


@pytest.mark.parametrize("limit", [0, 501, -1, 1000])
def test_limit_fuera_de_rango_retorna_422(limit):
    response = client.get(f"/api/tabla/raza?limit={limit}")
    assert response.status_code == 422


# ── asignar_tratamiento: umbrales exactos ─────────────────────────────────────

@pytest.mark.parametrize("hba1c,glucosa,nivel", [
    (5.6, 100, "Normal"),
    (5.7, 100, "Prediabetes"),
    (6.5, 100, "Diabetes leve"),
    (8.01, 100, "Diabetes moderada"),
    (10.01, 100, "Diabetes severa"),
    (4.0, 139, "Normal"),
    (4.0, 140, "Prediabetes"),
    (4.0, 200, "Diabetes leve"),
    (4.0, 301, "Diabetes moderada"),
    (4.0, 401, "Diabetes severa"),
])
def test_asignar_tratamiento_umbrales(hba1c, glucosa, nivel):
    assert asignar_tratamiento(hba1c, glucosa) == trat_map[nivel]


# ── ETL: timeout → HTTP 408 ───────────────────────────────────────────────────

def test_etl_timeout_retorna_408():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="load_data.py", timeout=300)):
        response = client.post("/api/cargar-dataset")
    assert response.status_code == 408
    assert response.json()["detail"] == "El proceso tardó demasiado."


# ── ETL: returncode != 0 → HTTP 500 con stderr ───────────────────────────────

def test_etl_error_retorna_500():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error en el ETL"
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        response = client.post("/api/cargar-dataset")
    assert response.status_code == 500
    assert response.json()["detail"] == "Error en el ETL"


# ── ETL: éxito → HTTP 200 con ok=True y log ──────────────────────────────────

def test_etl_exitoso_retorna_200():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "LISTO Carga completa."
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result):
        response = client.post("/api/cargar-dataset")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "LISTO" in data["log"]


# ── Empresa: cardinalidad de arrays ──────────────────────────────────────────

def test_empresa_cardinalidad():
    response = client.get("/api/empresa")
    assert response.status_code == 200
    data = response.json()
    assert len(data["objetivos_estrategicos"]) == 3
    assert len(data["objetivos_tacticos"]) == 3
    assert len(data["objetivos_operacionales"]) == 3
    assert len(data["problemas_sistemas"]) == 10
    assert len(data["problemas_decisiones"]) == 10


def test_empresa_campos_requeridos():
    response = client.get("/api/empresa")
    data = response.json()
    campos = {"nombre", "slogan", "mision", "vision",
              "objetivos_estrategicos", "objetivos_tacticos", "objetivos_operacionales",
              "problemas_sistemas", "problemas_decisiones"}
    assert set(data.keys()) == campos
