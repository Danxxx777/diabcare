"""Pruebas P15 — Integraciones."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from servicios.integraciones import IntegracionesServicio as svc  # noqa: E402

ADMIN = {"payload": {"sub": "1", "rol": "administrador", "correo": "admin@diabcare.com"}}
MEDICO = {"payload": {"sub": "3", "rol": "medico", "correo": "m@diabcare.com"}}


def test_estado_lista_integraciones():
    with patch("servicios.integraciones.IntegracionesServicio.verificar_conexion", return_value=True), \
         patch("servicios.integraciones.IntegracionesServicio._probar_http", return_value=False), \
         patch("servicios.integraciones.IntegracionesServicio._obtener_api_key_info",
               return_value={"configurada": False, "preview": "", "actualizada": None}):
        d = svc.estado()
    nombres = [i["nombre"] for i in d["integraciones"]]
    assert "MinIO" in nombres and "PocketBase" in nombres and "Apache Airflow" in nombres
    minio = next(i for i in d["integraciones"] if i["nombre"] == "MinIO")
    assert minio["estado"] == "conectado"
    assert d["api_publica"]["estado"] == "activa"


def test_generar_api_key_formato():
    cliente = MagicMock()
    cliente.bucket_exists.return_value = True
    with patch("servicios.integraciones.IntegracionesServicio.get_cliente", return_value=cliente):
        res = svc.generar_api_key("admin")
    assert res["api_key"].startswith("dc_")
    assert cliente.put_object.called


def test_endpoint_estado_admin_200(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=ADMIN), \
         patch("api.integraciones.IntegracionesRutas.estado",
               return_value={"integraciones": [], "api_publica": {"estado": "activa"}}):
        r = cliente_api.get("/api/integraciones/", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200


def test_endpoint_estado_medico_403(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=MEDICO):
        r = cliente_api.get("/api/integraciones/", headers={"Authorization": "Bearer x"})
    assert r.status_code == 403
