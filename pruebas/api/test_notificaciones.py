"""Pruebas P10 — Notificaciones."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from servicios.notificaciones import NotificacionesServicio as svc  # noqa: E402

ADMIN = {"payload": {"sub": "1", "rol": "administrador", "correo": "admin@diabcare.com"}}
MEDICO = {"payload": {"sub": "3", "rol": "medico", "correo": "m@diabcare.com"}}


def test_listar_vacio_devuelve_lista():
    cliente = MagicMock()
    cliente.get_object.side_effect = Exception("no existe")
    with patch("servicios.notificaciones.NotificacionesServicio.get_cliente", return_value=cliente):
        assert svc.listar() == []


def test_crear_persiste_y_normaliza_tipo():
    cliente = MagicMock()
    cliente.bucket_exists.return_value = True
    cliente.get_object.side_effect = Exception("no existe")
    with patch("servicios.notificaciones.NotificacionesServicio.get_cliente", return_value=cliente):
        res = svc.crear("Título", "Mensaje", "tipo_invalido")
    assert cliente.put_object.called
    assert "id" in res


def test_crear_es_resiliente_ante_error_minio():
    with patch("servicios.notificaciones.NotificacionesServicio.get_cliente",
               side_effect=Exception("minio caído")):
        res = svc.crear("Título", "Mensaje", "info")
    assert "error" in res  # no lanza excepción al llamador


def test_marcar_sin_notificaciones():
    cliente = MagicMock()
    cliente.get_object.side_effect = Exception("no existe")
    with patch("servicios.notificaciones.NotificacionesServicio.get_cliente", return_value=cliente):
        res = svc.marcar_todas_leidas()
    assert res["actualizadas"] == 0


def test_endpoint_listar_medico_200(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=MEDICO), \
         patch("api.notificaciones.NotificacionesRutas.listar", return_value=[]):
        r = cliente_api.get("/api/notificaciones/", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    assert r.json() == []


def test_endpoint_marcar_leidas_200(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=ADMIN), \
         patch("api.notificaciones.NotificacionesRutas.marcar_todas_leidas",
               return_value={"mensaje": "ok", "actualizadas": 2}):
        r = cliente_api.post("/api/notificaciones/marcar-leidas",
                             headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    assert r.json()["actualizadas"] == 2
