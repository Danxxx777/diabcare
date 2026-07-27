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
    "email_proveedor": "gmail",
    "email_brevo_api_key": "",
    "email_resend_api_key": "",
    "email_smtp_host": "smtp.gmail.com",
    "email_smtp_port": 587,
    "email_smtp_usuario": "",
    "email_smtp_password": "",
    "email_smtp_tls": True,
    "email_remitente": "",
    "email_remitente_nombre": "DiabCare Analytics",
    "email_destino_alertas": "",
    "email_destino_prueba": "",
    "email_cuentas": [],
    # id_plantilla → bool (activar/desactivar envío por categoría)
    "email_plantillas_activas": {},
}

# Claves que nunca se persisten aunque lleguen en el payload (seguridad).
_PROHIBIDAS = {"minio_secret", "secret_key", "password"}
_SECRETO_ENMASCARADO = "********"
_ROLES_CUENTA = ("remitente", "alerta", "prueba")


def _normalizar_cuentas(raw) -> list[dict]:
    out = []
    visto = set()
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        email = str(item.get("email") or "").strip().lower()
        if not email or "@" not in email or email in visto:
            continue
        visto.add(email)
        roles = [
            r for r in (item.get("roles") or [])
            if str(r).strip().lower() in _ROLES_CUENTA
        ]
        # dedupe roles preservando orden
        roles_u = []
        for r in roles:
            r = str(r).strip().lower()
            if r not in roles_u:
                roles_u.append(r)
        out.append({"email": email, "roles": roles_u})
    return out


def _cuentas_desde_legacy(cfg: dict) -> list[dict]:
    by = {}
    def add(email: str, role: str):
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            return
        by.setdefault(email, {"email": email, "roles": []})
        if role not in by[email]["roles"]:
            by[email]["roles"].append(role)

    rem = cfg.get("email_remitente") or cfg.get("email_smtp_usuario") or ""
    add(rem, "remitente")
    add(cfg.get("email_destino_alertas") or rem, "alerta")
    add(cfg.get("email_destino_prueba") or rem, "prueba")
    return list(by.values())


def _aplicar_roles_cuentas(cfg: dict) -> dict:
    """Deriva remitente / alertas / prueba desde email_cuentas."""
    cuentas = _normalizar_cuentas(cfg.get("email_cuentas"))
    if not cuentas:
        cuentas = _cuentas_desde_legacy(cfg)
    cfg["email_cuentas"] = cuentas

    def primero(role: str) -> str:
        for c in cuentas:
            if role in (c.get("roles") or []):
                return c["email"]
        return ""

    rem = primero("remitente") or (cuentas[0]["email"] if cuentas else "")
    alerta = primero("alerta") or rem
    prueba = primero("prueba") or alerta or rem
    if rem:
        cfg["email_remitente"] = rem
        if not (cfg.get("email_smtp_usuario") or "").strip():
            cfg["email_smtp_usuario"] = rem
        # Gmail: usuario SMTP = remitente
        if (cfg.get("email_proveedor") or "").lower() == "gmail":
            cfg["email_smtp_usuario"] = rem
    if alerta:
        cfg["email_destino_alertas"] = alerta
    if prueba:
        cfg["email_destino_prueba"] = prueba
    return cfg


def _enmascarar(cfg: dict) -> dict:
    out = dict(cfg)
    if out.get("email_smtp_password"):
        out["email_smtp_password"] = _SECRETO_ENMASCARADO
    if out.get("email_brevo_api_key"):
        out["email_brevo_api_key"] = _SECRETO_ENMASCARADO
    if out.get("email_resend_api_key"):
        out["email_resend_api_key"] = _SECRETO_ENMASCARADO
    return out


def obtener_configuracion(enmascarar_secretos: bool = True) -> dict:
    try:
        c = get_cliente()
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        guardado = json.loads(obj.read().decode("utf-8"))
    except Exception:
        guardado = {}
    cfg = {**DEFAULTS, **guardado}
    cfg = _aplicar_roles_cuentas(cfg)
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
    resend_key = limpio.get("email_resend_api_key")
    if resend_key in (None, "", _SECRETO_ENMASCARADO):
        limpio.pop("email_resend_api_key", None)

    if "email_cuentas" in limpio:
        limpio["email_cuentas"] = _normalizar_cuentas(limpio.get("email_cuentas"))

    if "email_plantillas_activas" in limpio:
        raw_flags = limpio.get("email_plantillas_activas") or {}
        if isinstance(raw_flags, dict):
            limpio["email_plantillas_activas"] = {
                str(k): bool(v) for k, v in raw_flags.items()
            }
        else:
            limpio.pop("email_plantillas_activas", None)

    nuevo = {**actual, **limpio}
    nuevo = _aplicar_roles_cuentas(nuevo)
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
