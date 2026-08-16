# -*- coding: utf-8 -*-
"""Smoke API hospitalaria P16-P20."""
import pytest

pytestmark = pytest.mark.api


def _auth(client, email="admin@diabcare.com", password="Admin2026*"):
    """
    Inicia sesión y deja la cookie en el cliente.

    Devuelve cabeceras vacías a propósito: la sesión dejó de viajar en un JWT
    de localStorage y ahora va en una cookie httpOnly que TestClient conserva.
    Se sigue devolviendo un dict para no tocar cada llamada de las pruebas.
    """
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo.get("usuario"), "el login debe identificar al usuario"
    token = cuerpo.get("token") or cuerpo.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def test_negocio_kpis(client):
    h = _auth(client)
    r = client.get("/api/dataset/negocio/kpis", headers=h)
    assert r.status_code in (200, 403)
    if r.status_code == 200:
        d = r.json()
        assert "facturado_total" in d
        assert "margen_farmacia" in d
        assert "urgencias" in d


def test_seguros_list(client):
    h = _auth(client)
    r = client.get("/api/seguros", headers=h)
    assert r.status_code in (200, 403)


def test_medicamentos_list(client):
    h = _auth(client)
    r = client.get("/api/medicamentos", headers=h)
    assert r.status_code in (200, 403)


def test_laboratorio_pruebas_list(client):
    h = _auth(client)
    r = client.get("/api/laboratorio/pruebas", headers=h)
    assert r.status_code in (200, 403)


def test_urgencias_list(client):
    h = _auth(client)
    r = client.get("/api/urgencias/", headers=h)
    assert r.status_code in (200, 403)


def test_rrhh_costeo(client):
    h = _auth(client)
    r = client.get("/api/rrhh/costeo", headers=h)
    assert r.status_code in (200, 403)


def test_factura_requiere_encounter(client):
    h = _auth(client)
    r = client.post("/api/facturas", headers=h, json={
        "id_paciente": "x", "subtotal": 10, "descuento": 0
    })
    if r.status_code not in (401, 403):
        assert r.status_code == 400
