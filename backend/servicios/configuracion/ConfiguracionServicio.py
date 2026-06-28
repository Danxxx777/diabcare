"""
ConfiguracionServicio — P12 Configuración del sistema (departamento Gobierno y
Cumplimiento). Gestiona los ajustes editables del sistema, persistidos como JSON
en MinIO `diabcare-app`. No almacena secretos (p. ej. claves secretas de MinIO).
"""

import io
import json

from servicios.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "configuracion/ajustes.json"

DEFAULTS = {
    "minio_endpoint": "localhost:9000",
    "minio_bucket": "diabetes-data",
    "minio_access": "admin",
    "debug": False,
    "auditoria": True,
    "cache": True,
    "email": False,
}

# Claves que nunca se persisten aunque lleguen en el payload (seguridad).
_PROHIBIDAS = {"minio_secret", "secret_key", "password"}


def obtener_configuracion() -> dict:
    try:
        c = get_cliente()
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        guardado = json.loads(obj.read().decode("utf-8"))
    except Exception:
        guardado = {}
    return {**DEFAULTS, **guardado}


def guardar_configuracion(datos: dict, usuario: str = "sistema") -> dict:
    actual = obtener_configuracion()
    limpio = {k: v for k, v in (datos or {}).items() if k not in _PROHIBIDAS}
    nuevo = {**actual, **limpio}
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        contenido = json.dumps(nuevo, ensure_ascii=False, indent=2).encode("utf-8")
        c.put_object(BUCKET_APP, ARCHIVO, io.BytesIO(contenido), length=len(contenido),
                     content_type="application/json")
    except Exception as e:
        return {"error": f"No se pudo guardar la configuración: {e}"}

    try:
        from servicios.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "update", "configuracion",
                  "Ajustes del sistema actualizados")
    except Exception:
        pass
    return {"mensaje": "Configuración guardada", "configuracion": nuevo}
