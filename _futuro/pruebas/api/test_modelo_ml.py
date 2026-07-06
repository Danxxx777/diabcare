"""Pruebas P14 — Gestión del Modelo ML."""
import os
import sys
from unittest.mock import patch

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from servicios.modelo_ml import ModeloMlServicio as svc  # noqa: E402

ADMIN = {"payload": {"sub": "1", "rol": "administrador", "correo": "admin@diabcare.com"}}
MEDICO = {"payload": {"sub": "3", "rol": "medico", "correo": "m@diabcare.com"}}
METRICAS = {"accuracy": 0.97, "precision": 0.95, "recall": 0.94, "f1": 0.945,
            "registros_entrenamiento": 800, "registros_prueba": 200}


def test_info_con_modelo_disponible():
    with patch("servicios.prediccion.PrediccionServicio.modelo_disponible", return_value=True), \
         patch("servicios.prediccion.PrediccionServicio.obtener_metricas", return_value=METRICAS):
        d = svc.info()
    assert d["disponible"] is True
    assert d["metricas"]["accuracy"] == 0.97
    assert d["algoritmo"] == "RandomForestClassifier"


def test_info_sin_modelo():
    with patch("servicios.prediccion.PrediccionServicio.modelo_disponible", return_value=False), \
         patch("servicios.prediccion.PrediccionServicio.obtener_metricas",
               return_value={"error": "Modelo no entrenado"}):
        d = svc.info()
    assert d["disponible"] is False
    assert d["metricas"] is None


def test_reentrenar_guarda_historial_y_audita():
    with patch("servicios.prediccion.PrediccionServicio.entrenar",
               return_value={"mensaje": "ok", **METRICAS}), \
         patch("servicios.modelo_ml.ModeloMlServicio._leer_historial", return_value=[]), \
         patch("servicios.modelo_ml.ModeloMlServicio._guardar_historial") as guardar, \
         patch("servicios.auditoria.AuditoriaServicio.registrar") as audit:
        res = svc.reentrenar("admin")
    assert res["accuracy"] == 0.97
    assert guardar.called
    assert audit.called


def test_reentrenar_error_no_guarda():
    with patch("servicios.prediccion.PrediccionServicio.entrenar",
               return_value={"error": "Dataset vacío"}), \
         patch("servicios.modelo_ml.ModeloMlServicio._guardar_historial") as guardar:
        res = svc.reentrenar("admin")
    assert "error" in res
    assert not guardar.called


def test_endpoint_info_admin_200(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=ADMIN), \
         patch("api.modelo_ml.ModeloMlRutas.info", return_value={"disponible": False}):
        r = cliente_api.get("/api/modelo-ml/info", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200


def test_endpoint_info_medico_403(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=MEDICO):
        r = cliente_api.get("/api/modelo-ml/info", headers={"Authorization": "Bearer x"})
    assert r.status_code == 403
