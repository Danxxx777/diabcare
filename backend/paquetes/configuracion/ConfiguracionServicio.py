"""
ConfiguracionServicio — P12 Configuración del sistema (departamento Gobierno y
Cumplimiento). Gestiona los ajustes editables del sistema, persistidos como JSON
en MinIO `diabcare-app`. No almacena secretos (p. ej. claves secretas de MinIO).
"""

import io
import json
import os

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
    "url_publica": "",
    "stripe_secret_key": "",
    "stripe_publishable_key": "",
    # Horario de atencion de la clinica. Urgencias queda fuera: es 24 h.
    # horario_dias: 0=lunes ... 6=domingo.
    "horario_apertura": "08:00",
    "horario_cierre": "18:00",
    "horario_dias": [0, 1, 2, 3, 4],
    # Identidad de la institucion: sale impresa en facturas y comprobantes.
    "institucion_nombre": "DiabCare Hospital",
    "institucion_ruc": "",
    "institucion_direccion": "",
    "institucion_telefono": "",
    "institucion_email": "",
    # Dias que se conservan las notificaciones ya leidas antes de poder purgarlas.
    "notificaciones_retencion_dias": 30,
    # IVA vigente (Ecuador paso de 12% a 15%): no deberia exigir tocar codigo.
    "iva_pct": 15.0,
    # Umbrales que disparan la alerta clinica automatica.
    "umbral_hba1c": 7.5,
    "umbral_glucosa": 180,
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
    env_sk = (os.getenv("STRIPE_SECRET_KEY") or os.getenv("DIABCARE_STRIPE_SECRET") or "").strip()
    if out.get("stripe_secret_key"):
        out["stripe_secret_key"] = _SECRETO_ENMASCARADO
        out["stripe_listo"] = True
    else:
        out["stripe_listo"] = env_sk.startswith("sk_")
    return out


def _num_config(clave: str, reserva: float) -> float:
    try:
        valor = (obtener_configuracion() or {}).get(clave)
        return float(valor) if valor not in (None, "") else float(reserva)
    except Exception:
        return float(reserva)


def iva_pct() -> float:
    """IVA vigente en tanto por ciento."""
    return max(0.0, min(100.0, _num_config("iva_pct", 15.0)))


def iva_factor() -> float:
    """Multiplicador para aplicar el IVA (1,15 con IVA al 15%)."""
    return 1.0 + iva_pct() / 100.0


def umbrales_clinicos() -> tuple:
    """(HbA1c, glucosa) a partir de los cuales se emite alerta."""
    return _num_config("umbral_hba1c", 7.5), _num_config("umbral_glucosa", 180)


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
    if "horario_apertura" in limpio or "horario_cierre" in limpio:
        apertura = str(limpio.get("horario_apertura") or actual.get("horario_apertura") or "")
        cierre = str(limpio.get("horario_cierre") or actual.get("horario_cierre") or "")
        if len(apertura) != 5 or len(cierre) != 5 or apertura >= cierre:
            return {"error": "El horario de cierre debe ser posterior a la apertura"}
    if "horario_dias" in limpio:
        dias = sorted({int(d) for d in (limpio.get("horario_dias") or []) if str(d).isdigit() and 0 <= int(d) <= 6})
        if not dias:
            return {"error": "Seleccione al menos un día de atención"}
        limpio["horario_dias"] = dias

    pwd = limpio.get("email_smtp_password")
    if pwd in (None, "", _SECRETO_ENMASCARADO):
        limpio.pop("email_smtp_password", None)
    brevo_key = limpio.get("email_brevo_api_key")
    if brevo_key in (None, "", _SECRETO_ENMASCARADO):
        limpio.pop("email_brevo_api_key", None)
    resend_key = limpio.get("email_resend_api_key")
    if resend_key in (None, "", _SECRETO_ENMASCARADO):
        limpio.pop("email_resend_api_key", None)
    stripe_key = limpio.get("stripe_secret_key")
    if stripe_key in (None, "", _SECRETO_ENMASCARADO):
        limpio.pop("stripe_secret_key", None)
    if "url_publica" in limpio:
        limpio["url_publica"] = str(limpio.get("url_publica") or "").strip().rstrip("/")

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
        registrar(
            usuario, "update", "configuracion", "Ajustes del sistema actualizados",
            antes=_enmascarar(actual), despues=_enmascarar(nuevo),
        )
    except Exception:
        pass
    return {"mensaje": "Configuración guardada", "configuracion": _enmascarar(nuevo)}
