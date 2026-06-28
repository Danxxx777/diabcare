"""Pruebas P12 — Configuración."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from servicios.configuracion import ConfiguracionServicio as svc  # noqa: E402

ADMIN = {"payload": {"sub": "1", "rol": "administrador", "correo": "admin@diabcare.com"}}
ANALISTA = {"payload": {"sub": "2", "rol": "analista", "correo": "a@diabcare.com"}}


def test_obtener_devuelve_defaults_si_no_hay_archivo():
    cliente = MagicMock()
    cliente.get_object.side_effect = Exception("no existe")
    with patch("servicios.configuracion.ConfiguracionServicio.get_cliente", return_value=cliente):
        cfg = svc.obtener_configuracion()
    assert cfg["minio_bucket"] == "diabetes-data"
    assert cfg["auditoria"] is True


def test_guardar_persiste_y_elimina_secretos():
    cliente = MagicMock()
    cliente.bucket_exists.return_value = True
    cliente.get_object.side_effect = Exception("no existe")
    with patch("servicios.configuracion.ConfiguracionServicio.get_cliente", return_value=cliente):
        res = svc.guardar_configuracion({"debug": True, "minio_secret": "SECRETO"}, "admin")
    assert cliente.put_object.called
    assert res["configuracion"]["debug"] is True
    assert "minio_secret" not in res["configuracion"]


def test_endpoint_guardar_admin_200(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=ADMIN), \
         patch("api.configuracion.ConfiguracionRutas.guardar_configuracion",
               return_value={"mensaje": "ok", "configuracion": {}}):
        r = cliente_api.post("/api/configuracion/", headers={"Authorization": "Bearer x"},
                             json={"debug": True})
    assert r.status_code == 200


def test_endpoint_guardar_analista_403(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=ANALISTA):
        r = cliente_api.post("/api/configuracion/", headers={"Authorization": "Bearer x"},
                             json={"debug": True})
    assert r.status_code == 403
