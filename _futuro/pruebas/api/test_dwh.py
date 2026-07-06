"""Pruebas API — materializacion DWH (GA07)."""
from unittest.mock import patch

ANALISTA = {"payload": {"sub": "2", "rol": "analista", "correo": "a@diabcare.com"}}


def test_dwh_resumen_requiere_auth(cliente_api):
    r = cliente_api.get("/api/dataset/dwh/resumen")
    assert r.status_code in (401, 403)


def test_dwh_reconstruir_analista(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=ANALISTA), \
         patch("api.dataset.DatasetRutas.materializar_dwh", return_value={"ok": True, "hechos": 5}):
        r = cliente_api.post("/api/dataset/dwh/reconstruir", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_dimension_tiempo(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=ANALISTA), \
         patch("api.dataset.DatasetRutas.leer_dimension", return_value={"datos": [{"id_tiempo": 1, "year": 2025}], "total": 1}):
        r = cliente_api.get("/api/dataset/dimension/tiempo", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    assert r.json()["total"] == 1
