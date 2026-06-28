"""
IntegracionesServicio — P15 API pública e integraciones (departamento Crecimiento
e Integraciones). Reporta el estado de las integraciones reales del stack
(MinIO, PocketBase, Airflow) y gestiona una clave de API pública persistida en
MinIO `diabcare-app/integraciones/api_key.json`.
"""

import io
import json
import secrets
import urllib.request
from datetime import datetime

from servicios.configuracion.ConfiguracionClienteMinio import get_cliente, verificar_conexion
from servicios.configuracion.ConfiguracionAjustes import POCKETBASE_URL

BUCKET_APP = "diabcare-app"
ARCHIVO_KEY = "integraciones/api_key.json"


def _probar_http(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def estado() -> dict:
    minio_ok = False
    try:
        minio_ok = bool(verificar_conexion())
    except Exception:
        minio_ok = False

    pocketbase_ok = _probar_http(f"{POCKETBASE_URL}/api/health")
    airflow_ok = _probar_http("http://localhost:8080/health")

    integraciones = [
        {"nombre": "MinIO", "tipo": "Almacenamiento de objetos",
         "url": "localhost:9000", "estado": "conectado" if minio_ok else "sin conexión"},
        {"nombre": "PocketBase", "tipo": "Fuente de datos",
         "url": POCKETBASE_URL, "estado": "conectado" if pocketbase_ok else "sin conexión"},
        {"nombre": "Apache Airflow", "tipo": "Orquestación ELT",
         "url": "localhost:8080", "estado": "conectado" if airflow_ok else "sin conexión"},
    ]

    key_info = _obtener_api_key_info()
    return {
        "integraciones": integraciones,
        "api_publica": {
            "estado": "activa",
            "documentacion": "http://localhost:8000/docs",
            "openapi": "http://localhost:8000/openapi.json",
            "api_key_configurada": key_info["configurada"],
            "api_key_preview": key_info["preview"],
            "api_key_actualizada": key_info["actualizada"],
        },
    }


def _obtener_api_key_info() -> dict:
    try:
        c = get_cliente()
        obj = c.get_object(BUCKET_APP, ARCHIVO_KEY)
        data = json.loads(obj.read().decode("utf-8"))
        key = data.get("api_key", "")
        return {
            "configurada": bool(key),
            "preview": (key[:8] + "..." + key[-4:]) if key else "",
            "actualizada": data.get("actualizada"),
        }
    except Exception:
        return {"configurada": False, "preview": "", "actualizada": None}


def generar_api_key(usuario: str = "sistema") -> dict:
    nueva = "dc_" + secrets.token_hex(24)
    data = {"api_key": nueva, "actualizada": datetime.now().isoformat(), "por": usuario}
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        contenido = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        c.put_object(BUCKET_APP, ARCHIVO_KEY, io.BytesIO(contenido), length=len(contenido),
                     content_type="application/json")
    except Exception as e:
        return {"error": f"No se pudo generar la clave: {e}"}

    try:
        from servicios.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "create", "integraciones", "Nueva clave de API pública generada")
    except Exception:
        pass
    # Se devuelve la clave completa solo en el momento de generarla.
    return {"mensaje": "Clave de API generada", "api_key": nueva,
            "actualizada": data["actualizada"]}
