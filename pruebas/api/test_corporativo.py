"""Pruebas P9 — Corporativo."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from servicios.corporativo import CorporativoServicio as svc  # noqa: E402

ADMIN = {"payload": {"sub": "1", "rol": "administrador", "correo": "admin@diabcare.com"}}
MEDICO = {"payload": {"sub": "3", "rol": "medico", "correo": "m@diabcare.com"}}


def test_obtener_devuelve_defaults():
    cliente = MagicMock()
    cliente.get_object.side_effect = Exception("no existe")
    with patch("servicios.corporativo.CorporativoServicio.get_cliente", return_value=cliente):
        info = svc.obtener()
    assert info["nombre"] == "DiabCare Analytics"
    assert isinstance(info["objetivos_estrategicos"], list)


def test_actualizar_persiste_solo_campos_validos():
    cliente = MagicMock()
    cliente.bucket_exists.return_value = True
    cliente.get_object.side_effect = Exception("no existe")
    with patch("servicios.corporativo.CorporativoServicio.get_cliente", return_value=cliente):
        res = svc.actualizar({"vision": "Nueva visión", "campo_basura": "x"}, "admin")
    assert cliente.put_object.called
    assert res["corporativo"]["vision"] == "Nueva visión"
    assert "campo_basura" not in res["corporativo"]


def test_endpoint_obtener_autenticado_200(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=MEDICO), \
         patch("api.corporativo.CorporativoRutas.obtener", return_value={"nombre": "DiabCare Analytics"}):
        r = cliente_api.get("/api/corporativo/", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    assert r.json()["nombre"] == "DiabCare Analytics"


def test_endpoint_actualizar_medico_403(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=MEDICO):
        r = cliente_api.put("/api/corporativo/", headers={"Authorization": "Bearer x"},
                            json={"vision": "x"})
    assert r.status_code == 403
