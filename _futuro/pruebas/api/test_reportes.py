"""
Pruebas P7 — Reportes PDF.

Cubren:
  - Generación del PDF (bytes válidos) con/sin métricas del modelo (US1, US2).
  - Resumen de registros filtrados, incluido el caso sin resultados (US3).
  - Listado y descarga de reportes (US4), incluido 404.
  - Verificación de privacidad: el PDF no incluye identificadores de paciente.

Las pruebas de servicio mockean MinIO y las fuentes de datos, por lo que se
ejecutan sin un stack en vivo. Las pruebas de endpoint se saltan con elegancia
si la app (Principal:app) no puede importarse en el entorno actual.
"""

import io
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# backend al path para importar el servicio real
BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

pd = pytest.importorskip("pandas")
pytest.importorskip("fpdf")

from servicios.reportes import ReportesServicio as svc  # noqa: E402


# ---------------------------------------------------------------------------
# Datos de apoyo
# ---------------------------------------------------------------------------
def _estadisticas_demo():
    return {
        "total": 100,
        "con_diabetes": 40,
        "sin_diabetes": 60,
        "genero": {"Male": 55, "Female": 45},
        "promedios": {
            "bmi": {"con": 31.2, "sin": 26.4},
            "hba1c": {"con": 7.1, "sin": 5.4},
            "glucosa": {"con": 165.0, "sin": 110.0},
        },
    }


def _metricas_demo():
    return {
        "accuracy": 0.95, "precision": 0.92, "recall": 0.90, "f1": 0.91,
        "registros_entrenamiento": 800, "registros_prueba": 200,
    }


def _df_demo():
    return pd.DataFrame({
        "encounter_id": [1, 2, 3, 4],
        "gender": ["Male", "Female", "Male", "Female"],
        "age": [25, 45, 65, 70],
        "location": ["Alabama", "Texas", "Alabama", "Ohio"],
        "diabetes": [0, 1, 1, 0],
        "bmi": [22.0, 30.0, 28.0, 26.0],
        "hbA1c_level": [5.0, 7.0, 6.5, 5.5],
        "blood_glucose_level": [100, 180, 160, 120],
    })


# ---------------------------------------------------------------------------
# US1 + US2 — Generación de PDF con estadísticas y métricas
# ---------------------------------------------------------------------------
def test_generar_pdf_devuelve_bytes_pdf_con_metricas():
    with patch("servicios.registros_clinicos.RegistrosClinicosServicio.estadisticas",
               return_value=_estadisticas_demo()), \
         patch("servicios.prediccion.PrediccionServicio.obtener_metricas",
               return_value=_metricas_demo()), \
         patch("servicios.registros_clinicos.RegistrosClinicosServicio._extraer",
               return_value=_df_demo()):
        contenido = svc.generar_pdf({}, "tester")

    assert isinstance(contenido, (bytes, bytearray))
    assert contenido[:4] == b"%PDF"
    assert len(contenido) > 500


def test_generar_pdf_sin_modelo_no_falla():
    with patch("servicios.registros_clinicos.RegistrosClinicosServicio.estadisticas",
               return_value=_estadisticas_demo()), \
         patch("servicios.prediccion.PrediccionServicio.obtener_metricas",
               return_value={"error": "Modelo no entrenado"}), \
         patch("servicios.registros_clinicos.RegistrosClinicosServicio._extraer",
               return_value=_df_demo()):
        contenido = svc.generar_pdf({}, "tester")
    assert contenido[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# US3 — Resumen de registros filtrados
# ---------------------------------------------------------------------------
def test_resumen_filtrado_coincide_con_filtro():
    with patch("servicios.registros_clinicos.RegistrosClinicosServicio._extraer",
               return_value=_df_demo()):
        resumen = svc._resumen_filtrado({"diabetes": 1})
    assert resumen["total"] == 2
    assert resumen["con_diabetes"] == 2
    assert resumen["sin_diabetes"] == 0


def test_resumen_filtrado_sin_resultados():
    with patch("servicios.registros_clinicos.RegistrosClinicosServicio._extraer",
               return_value=_df_demo()):
        resumen = svc._resumen_filtrado({"location": "Narnia"})
    assert resumen["total"] == 0


def test_resumen_filtrado_rango_edad():
    with patch("servicios.registros_clinicos.RegistrosClinicosServicio._extraer",
               return_value=_df_demo()):
        resumen = svc._resumen_filtrado({"age_min": 60, "age_max": 80})
    assert resumen["total"] == 2


# ---------------------------------------------------------------------------
# Privacidad — el PDF no debe contener identificadores de paciente
# ---------------------------------------------------------------------------
def test_pdf_no_incluye_encounter_id():
    with patch("servicios.registros_clinicos.RegistrosClinicosServicio.estadisticas",
               return_value=_estadisticas_demo()), \
         patch("servicios.prediccion.PrediccionServicio.obtener_metricas",
               return_value=_metricas_demo()), \
         patch("servicios.registros_clinicos.RegistrosClinicosServicio._extraer",
               return_value=_df_demo()):
        contenido = bytes(svc.generar_pdf({"diabetes": 1}, "tester"))
    assert b"encounter_id" not in contenido


# ---------------------------------------------------------------------------
# US1 — Generar y subir (persistencia en MinIO)
# ---------------------------------------------------------------------------
def test_generar_y_subir_persiste_y_devuelve_metadatos():
    cliente = MagicMock()
    cliente.bucket_exists.return_value = True
    with patch("servicios.reportes.ReportesServicio.get_cliente", return_value=cliente), \
         patch("servicios.registros_clinicos.RegistrosClinicosServicio.estadisticas",
               return_value=_estadisticas_demo()), \
         patch("servicios.prediccion.PrediccionServicio.obtener_metricas",
               return_value=_metricas_demo()), \
         patch("servicios.registros_clinicos.RegistrosClinicosServicio._extraer",
               return_value=_df_demo()):
        meta = svc.generar_y_subir({}, "tester")

    assert cliente.put_object.called
    assert meta["nombre"].startswith("reporte_")
    assert meta["nombre"].endswith(".pdf")
    assert meta["ruta"].startswith("diabcare-app/reportes/")
    assert "fecha" in meta and "tamano_mb" in meta


# ---------------------------------------------------------------------------
# US4 — Listar y descargar
# ---------------------------------------------------------------------------
def test_listar_reportes_parsea_objetos():
    obj = MagicMock()
    obj.object_name = "reportes/reporte_20260101_120000.pdf"
    obj.size = 2048
    from datetime import datetime
    obj.last_modified = datetime(2026, 1, 1, 12, 0, 0)

    cliente = MagicMock()
    cliente.bucket_exists.return_value = True
    cliente.list_objects.return_value = [obj]
    with patch("servicios.reportes.ReportesServicio.get_cliente", return_value=cliente):
        reportes = svc.listar_reportes()

    assert len(reportes) == 1
    assert reportes[0]["nombre"] == "reporte_20260101_120000.pdf"
    assert reportes[0]["tamano_mb"] == round(2048 / (1024 * 1024), 4)


def test_descargar_reporte_existente():
    respuesta = MagicMock()
    respuesta.read.return_value = b"%PDF-1.4 demo"
    cliente = MagicMock()
    cliente.get_object.return_value = respuesta
    with patch("servicios.reportes.ReportesServicio.get_cliente", return_value=cliente):
        contenido = svc.descargar_reporte("reporte_x.pdf")
    assert contenido == b"%PDF-1.4 demo"


def test_descargar_reporte_inexistente_devuelve_none():
    cliente = MagicMock()
    cliente.get_object.side_effect = Exception("NoSuchKey")
    with patch("servicios.reportes.ReportesServicio.get_cliente", return_value=cliente):
        contenido = svc.descargar_reporte("no_existe.pdf")
    assert contenido is None


# ---------------------------------------------------------------------------
# Endpoints (se saltan si la app no puede importarse en este entorno)
# ---------------------------------------------------------------------------
@pytest.fixture
def cliente_api():
    """TestClient sobre Principal:app, con cwd en backend para los StaticFiles."""
    from fastapi.testclient import TestClient
    cwd = os.getcwd()
    os.chdir(BACKEND)
    try:
        try:
            from Principal import app
        except Exception as e:  # entorno sin static dirs / dependencias
            pytest.skip(f"No se pudo importar Principal:app: {e}")
        yield TestClient(app)
    finally:
        os.chdir(cwd)


def _payload_admin():
    return {"payload": {"sub": "admin", "rol": "administrador", "correo": "admin@diabcare"}}


def test_endpoint_generar_200(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=_payload_admin()), \
         patch("api.reportes.ReportesRutas.generar_y_subir",
               return_value={"nombre": "reporte_x.pdf", "ruta": "diabcare-app/reportes/reporte_x.pdf",
                             "fecha": "2026-01-01T00:00:00", "tamano_mb": 0.01}):
        r = cliente_api.post("/api/reportes/generar",
                             headers={"Authorization": "Bearer x"}, json={})
    assert r.status_code == 200
    assert r.json()["nombre"] == "reporte_x.pdf"


def test_endpoint_generar_filtros_invalidos_400(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=_payload_admin()):
        r = cliente_api.post("/api/reportes/generar",
                             headers={"Authorization": "Bearer x"},
                             json={"age_min": 80, "age_max": 20})
    assert r.status_code == 400


def test_endpoint_descargar_404(cliente_api):
    with patch("utilidades.Dependencias.verificar_token", return_value=_payload_admin()), \
         patch("api.reportes.ReportesRutas.descargar_reporte", return_value=None):
        r = cliente_api.get("/api/reportes/no_existe.pdf",
                            headers={"Authorization": "Bearer x"})
    assert r.status_code == 404
