"""
ConfiguracionServicio — P12 Configuración del sistema (departamento Gobierno y
Cumplimiento). Gestiona los ajustes editables del sistema, persistidos como JSON
en MinIO `diabcare-app`. No almacena secretos (p. ej. claves secretas de MinIO).
"""

import io
import json

from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

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
    "email_proveedor": "brevo",
    "email_brevo_api_key": "",
    "email_smtp_host": "smtp-relay.brevo.com",
    "email_smtp_port": 587,
    "email_smtp_usuario": "",
    "email_smtp_password": "",
    "email_smtp_tls": True,
    "email_remitente": "",
    "email_remitente_nombre": "DiabCare Analytics",
    "email_destino_alertas": "",
}

# Claves que nunca se persisten aunque lleguen en el payload (seguridad).
_PROHIBIDAS = {"minio_secret", "secret_key", "password"}
_SECRETO_ENMASCARADO = "********"


def _enmascarar(cfg: dict) -> dict:
    out = dict(cfg)
    if out.get("email_smtp_password"):
        out["email_smtp_password"] = _SECRETO_ENMASCARADO
    if out.get("email_brevo_api_key"):
        out["email_brevo_api_key"] = _SECRETO_ENMASCARADO
    return out


def obtener_configuracion(enmascarar_secretos: bool = True) -> dict:
    try:
        c = get_cliente()
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        guardado = json.loads(obj.read().decode("utf-8"))
    except Exception:
        guardado = {}
    cfg = {**DEFAULTS, **guardado}
    return _enmascarar(cfg) if enmascarar_secretos else cfg


def guardar_configuracion(datos: dict, usuario: str = "sistema") -> dict:
    actual = obtener_configuracion(enmascarar_secretos=False)
    limpio = {k: v for k, v in (datos or {}).items() if k not in _PROHIBIDAS}

    pwd = limpio.get("email_smtp_password")
    if pwd in (None, "", _SECRETO_ENMASCARADO):
        limpio.pop("email_smtp_password", None)
    brevo_key = limpio.get("email_brevo_api_key")
    if brevo_key in (None, "", _SECRETO_ENMASCARADO):
        limpio.pop("email_brevo_api_key", None)

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
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "update", "configuracion",
                  "Ajustes del sistema actualizados")
    except Exception:
        pass
    return {"mensaje": "Configuración guardada", "configuracion": _enmascarar(nuevo)}
