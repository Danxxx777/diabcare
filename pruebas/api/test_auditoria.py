"""Pruebas P11 — Auditoría."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

pd = pytest.importorskip("pandas")
from servicios.auditoria import AuditoriaServicio as svc  # noqa: E402

ADMIN = {"payload": {"sub": "1", "rol": "administrador", "correo": "admin@diabcare.com"}}
MEDICO = {"payload": {"sub": "3", "rol": "medico", "correo": "medico@diabcare.com"}}


def _df():
    return pd.DataFrame([
        {"id": "a", "fecha": "2026-06-19T10:00:00", "usuario": "admin", "tipo": "login", "modulo": "autenticacion", "detalle": "ok"},
        {"id": "b", "fecha": "2026-06-19T11:00:00", "usuario": "admin", "tipo": "error", "modulo": "modelo_ml", "detalle": "x"},
    ])


def test_listar_pagina_y_ordena():
    with patch("servicios.auditoria.AuditoriaServicio._extraer", return_value=_df()):
        res = svc.listar(skip=0, limit=10)
    assert res["total"] == 2
    assert res["eventos"][0]["fecha"] >= res["eventos"][1]["fecha"]  # desc


def test_listar_filtra_por_tipo():
    with patch("servicios.auditoria.AuditoriaServicio._extraer", return_value=_df()):
        res = svc.listar(tipo="error")
    assert res["total"] == 1
    assert res["eventos"][0]["tipo"] == "error"


def test_estadisticas():
    with patch("servicios.auditoria.AuditoriaServicio._extraer", return_value=_df()):
        st = svc.estadisticas()
    assert st["total"] == 2 and st["errores"] == 1 and st["usuarios"] == 1


def test_registrar_persiste_y_es_resiliente():
    cliente = MagicMock()
    cliente.bucket_exists.return_value = True
    cliente.get_object.side_effect = Exception("vacío")  # primera vez sin archivo
    with patch("servicios.auditoria.AuditoriaServicio.get_cliente", return_value=cliente):
        svc.registrar("admin", "create", "reportes", "demo")
    assert cliente.put_object.called


def test_registrar_no_lanza_aunque_falle():
    with patch("servicios.auditoria.AuditoriaServicio.get_cliente", side_effect=Exception("down")):
        svc.registrar("admin", "create", "reportes", "demo")  # no debe lanzar


def test_endpoint_listar_admin_200(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=ADMIN), \
         patch("api.auditoria.AuditoriaRutas.listar", return_value={"total": 0, "eventos": []}):
        r = cliente_api.get("/api/auditoria/", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200


def test_endpoint_listar_medico_403(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=MEDICO):
        r = cliente_api.get("/api/auditoria/", headers={"Authorization": "Bearer x"})
    assert r.status_code == 403
