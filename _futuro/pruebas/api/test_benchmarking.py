"""Pruebas P13 — Benchmarking."""
import os
import sys
from unittest.mock import patch

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from servicios.benchmarking import BenchmarkingServicio as svc  # noqa: E402

ADMIN = {"payload": {"sub": "1", "rol": "administrador", "correo": "admin@diabcare.com"}}
ANALISTA = {"payload": {"sub": "2", "rol": "analista", "correo": "a@diabcare.com"}}

METRICAS = {"accuracy": 0.97, "precision": 0.95, "recall": 0.92, "f1": 0.93}


def test_comparativa_marca_cumplimiento():
    with patch("servicios.prediccion.PrediccionServicio.obtener_metricas", return_value=METRICAS), \
         patch("servicios.prediccion.PrediccionServicio.modelo_disponible", return_value=True), \
         patch("servicios.registros_clinicos.RegistrosClinicosServicio.estadisticas",
               return_value={"total": 1000}):
        d = svc.comparativa()
    acc = next(i for i in d["indicadores"] if i["indicador"].startswith("Exactitud"))
    assert acc["cumple"] is True
    assert d["resumen"]["medibles"] >= 4
    assert d["resumen"]["cumplidos"] >= 1


def test_comparativa_sin_modelo_no_revienta():
    with patch("servicios.prediccion.PrediccionServicio.obtener_metricas",
               return_value={"error": "Modelo no entrenado"}), \
         patch("servicios.prediccion.PrediccionServicio.modelo_disponible", return_value=False), \
         patch("servicios.registros_clinicos.RegistrosClinicosServicio.estadisticas",
               return_value={"total": 0}):
        d = svc.comparativa()
    acc = next(i for i in d["indicadores"] if i["indicador"].startswith("Exactitud"))
    assert acc["actual"] is None
    assert acc["cumple"] is None


def test_endpoint_admin_200(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=ADMIN), \
         patch("api.benchmarking.BenchmarkingRutas.comparativa",
               return_value={"indicadores": [], "resumen": {"medibles": 0, "cumplidos": 0}}):
        r = cliente_api.get("/api/benchmarking/", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200


def test_endpoint_analista_403(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=ANALISTA):
        r = cliente_api.get("/api/benchmarking/", headers={"Authorization": "Bearer x"})
    assert r.status_code == 403
