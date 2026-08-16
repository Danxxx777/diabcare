"""Smoke tests DiabCare Hospital — P16–P20 (requiere API + MinIO)."""
import os
import pytest
import requests

BASE = os.getenv("DIABCARE_API", "http://localhost:8000")


@pytest.fixture(scope="module")
def token():
    r = requests.post(
        f"{BASE}/api/auth/login",
        json={"email": "admin@diabcare.com", "password": "Admin2026*"},
        timeout=30,
    )
    if r.status_code != 200:
        pytest.skip("API no disponible o credenciales demo ausentes")
    return r.json().get("token") or r.json().get("access_token")


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def test_factura_crud_logico(token):
    r = requests.post(
        f"{BASE}/api/facturas",
        headers=_h(token),
        json={"encounter_id": "enc-demo-1", "id_paciente": "pac-1", "subtotal": 100, "descuento": 0},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    fid = r.json()["id_factura"]
    assert requests.get(f"{BASE}/api/facturas/{fid}", headers=_h(token), timeout=30).status_code == 200
    assert requests.delete(f"{BASE}/api/facturas/{fid}", headers=_h(token), timeout=30).status_code == 200
    d = requests.get(f"{BASE}/api/facturas/{fid}", headers=_h(token), timeout=30).json()
    assert str(d.get("estado", "")).startswith("anul")


def test_medicamento_y_seed(token):
    requests.post(f"{BASE}/api/farmacia/seed", headers=_h(token), timeout=30)
    r = requests.get(f"{BASE}/api/medicamentos", headers=_h(token), timeout=30)
    assert r.status_code == 200
    assert r.json().get("total", 0) >= 1


def test_urgencia_triage(token):
    r = requests.post(
        f"{BASE}/api/urgencias/",
        headers=_h(token),
        json={"id_paciente": "pac-1", "triage": "III", "motivo": "hipoglucemia"},
        timeout=30,
    )
    assert r.status_code == 200, r.text


def test_comorbilidad(token):
    r = requests.post(
        f"{BASE}/api/comorbilidades/",
        headers=_h(token),
        json={
            "id_paciente": "pac-1",
            "tipo": "retinopatia",
            "fecha_deteccion": "2026-07-01",
            "id_medico": "med-1",
        },
        timeout=30,
    )
    assert r.status_code == 200, r.text


def test_rrhh_seed(token):
    assert requests.post(f"{BASE}/api/rrhh/seed", headers=_h(token), timeout=30).status_code == 200
    assert requests.get(f"{BASE}/api/rrhh/cargos", headers=_h(token), timeout=30).status_code == 200
