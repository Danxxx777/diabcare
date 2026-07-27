"""
Envío de correo: Brevo (API), Resend (API gratis), SMTP / Mailpit (local OSS).
"""

from __future__ import annotations

import json
import smtplib
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from paquetes.configuracion.ConfiguracionServicio import obtener_configuracion
from paquetes.configuracion.ConfiguracionEmailPlantillas import CATALOGO_CORREOS, ROLES_CUENTA

PRESETS = {
    "gmail": {
        "email": True,
        "email_proveedor": "gmail",
        "email_smtp_host": "smtp.gmail.com",
        "email_smtp_port": 587,
        "email_smtp_tls": True,
        "email_smtp_usuario": "",
        "email_smtp_password": "",
        "email_remitente": "",
        "email_remitente_nombre": "DiabCare Analytics",
    },
    "mailpit": {
        "email": True,
        "email_proveedor": "mailpit",
        "email_smtp_host": "127.0.0.1",
        "email_smtp_port": 1025,
        "email_smtp_usuario": "",
        "email_smtp_password": "",
        "email_smtp_tls": False,
        "email_remitente": "noreply@diabcare.local",
        "email_remitente_nombre": "DiabCare Analytics",
    },
}


def _cfg() -> dict:
    return obtener_configuracion(enmascarar_secretos=False)


def plantilla_habilitada(categoria: str, cfg: dict | None = None) -> bool:
    """Si la categoría está apagada en Configuración, no se envía."""
    cfg = cfg or _cfg()
    flags = cfg.get("email_plantillas_activas") or {}
    if not isinstance(flags, dict):
        return True
    cat = (categoria or "").strip().lower()
    if cat not in flags:
        return True
    return bool(flags[cat])


def _remitente(cfg: dict) -> tuple[str, str]:
    usuario = (cfg.get("email_smtp_usuario") or "").strip()
    remitente = (cfg.get("email_remitente") or usuario).strip()
    nombre = (cfg.get("email_remitente_nombre") or "DiabCare Analytics").strip()
    return remitente, nombre


def estado_correo() -> dict:
    """Diagnóstico para la UI: qué falta para poder enviar."""
    cfg = _cfg()
    proveedor = (cfg.get("email_proveedor") or "brevo").strip().lower()
    enabled = bool(cfg.get("email"))
    rem, _ = _remitente(cfg)
    checklist = []
    listo = True

    if not enabled:
        checklist.append({"ok": False, "texto": "Active «Habilitar envío de correos» y guarde"})
        listo = False
    else:
        checklist.append({"ok": True, "texto": "Envío de correos habilitado"})

    if proveedor == "brevo":
        key = (cfg.get("email_brevo_api_key") or "").strip()
        if not key:
            checklist.append({"ok": False, "texto": "Falta API key de Brevo (xkeysib-…)"})
            listo = False
        else:
            checklist.append({"ok": True, "texto": "API key Brevo configurada"})
        if not rem:
            checklist.append({"ok": False, "texto": "Falta correo remitente (debe estar verificado en Brevo)"})
            listo = False
        else:
            checklist.append({"ok": True, "texto": f"Remitente: {rem}"})
        checklist.append({
            "ok": True,
            "texto": "Brevo gratis: verifique el remitente en app.brevo.com → Senders",
        })
    elif proveedor == "gmail":
        usuario = (cfg.get("email_smtp_usuario") or rem or "").strip()
        pwd = (cfg.get("email_smtp_password") or "").strip()
        if not usuario or "@" not in usuario:
            checklist.append({"ok": False, "texto": "Indique su Gmail completo como usuario SMTP / remitente"})
            listo = False
        else:
            checklist.append({"ok": True, "texto": f"Cuenta Gmail: {usuario}"})
        if not pwd or len(pwd) < 10:
            checklist.append({
                "ok": False,
                "texto": "Falta contraseña de aplicación de Google (16 caracteres, no la clave normal)",
            })
            listo = False
        else:
            checklist.append({"ok": True, "texto": "Contraseña de aplicación configurada"})
        host = (cfg.get("email_smtp_host") or "smtp.gmail.com").strip()
        checklist.append({"ok": True, "texto": f"SMTP {host}:{cfg.get('email_smtp_port') or 587} + TLS"})
        checklist.append({
            "ok": True,
            "texto": "Requiere verificación en 2 pasos + App Password: myaccount.google.com/apppasswords",
        })
        if usuario and "@" in usuario and not usuario.lower().endswith(("@gmail.com", "@googlemail.com")):
            checklist.append({
                "ok": True,
                "texto": (
                    "Cuenta Google Workspace (@institucional): el administrador "
                    "debe permitir «contraseñas de aplicaciones»"
                ),
            })
    elif proveedor == "resend":
        key = (cfg.get("email_resend_api_key") or "").strip()
        if not key:
            checklist.append({"ok": False, "texto": "Falta API key de Resend (re_…)"})
            listo = False
        else:
            checklist.append({"ok": True, "texto": "API key Resend configurada"})
        if not rem:
            checklist.append({"ok": False, "texto": "Falta remitente (dominio verificado o onboarding@resend.dev en demo)"})
            listo = False
        else:
            checklist.append({"ok": True, "texto": f"Remitente: {rem}"})
    elif proveedor in ("mailpit", "smtp"):
        host = (cfg.get("email_smtp_host") or "").strip()
        if not host:
            checklist.append({"ok": False, "texto": "Falta servidor SMTP"})
            listo = False
        else:
            checklist.append({
                "ok": True,
                "texto": f"SMTP {host}:{cfg.get('email_smtp_port') or 587}"
                + (" (Mailpit — vea http://127.0.0.1:8025)" if proveedor == "mailpit" else ""),
            })
        if not rem:
            checklist.append({"ok": False, "texto": "Falta correo remitente"})
            listo = False
        else:
            checklist.append({"ok": True, "texto": f"Remitente: {rem}"})
        if proveedor == "mailpit":
            checklist.append({
                "ok": True,
                "texto": "Mailpit es local: el correo no llega a Gmail; se captura en la bandeja web :8025",
            })
    else:
        checklist.append({"ok": False, "texto": f"Proveedor desconocido: {proveedor}"})
        listo = False

    flags = cfg.get("email_plantillas_activas") or {}
    if not isinstance(flags, dict):
        flags = {}
    catalogo = [
        {
            **item,
            "activo": bool(flags.get(item["id"], True)),
            "audiencia_label": {
                "paciente": "Pacientes",
                "rol": "Roles app",
                "sistema": "Sistema",
            }.get(item.get("audiencia", ""), item.get("audiencia", "")),
        }
        for item in CATALOGO_CORREOS
    ]

    return {
        "habilitado": enabled,
        "listo": listo and enabled,
        "proveedor": proveedor,
        "remitente": rem,
        "checklist": checklist,
        "catalogo": catalogo,
        "roles_cuenta": ROLES_CUENTA,
        "email_plantillas_activas": {
            item["id"]: bool(flags.get(item["id"], True)) for item in CATALOGO_CORREOS
        },
        "guias": {
            "gmail": "https://myaccount.google.com/apppasswords",
            "brevo": "https://app.brevo.com/settings/keys/api",
            "resend": "https://resend.com/api-keys",
            "mailpit": "https://github.com/axllent/mailpit",
        },
    }


def _enviar_brevo(
    destino: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str | None,
    cfg: dict,
) -> dict:
    api_key = (cfg.get("email_brevo_api_key") or "").strip()
    if not api_key:
        return {"error": "Configure la API key de Brevo (email_brevo_api_key)"}

    remitente, nombre = _remitente(cfg)
    if not remitente:
        return {"error": "Configure el correo remitente (debe estar verificado en Brevo)"}

    payload = {
        "sender": {"name": nombre, "email": remitente},
        "to": [{"email": destino}],
        "subject": asunto,
        "textContent": cuerpo_texto,
    }
    if cuerpo_html:
        payload["htmlContent"] = cuerpo_html

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=data,
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            if resp.status not in (200, 201, 202, 204):
                return {"error": f"Brevo respondió HTTP {resp.status}"}
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
            det = json.loads(body).get("message", body) if body else str(e)
        except Exception:
            det = str(e)
        if e.code == 401:
            return {"error": "API key de Brevo inválida"}
        return {"error": f"Brevo: {det}"}
    except urllib.error.URLError as e:
        return {"error": f"No se pudo contactar a Brevo: {e.reason}"}

    return {"mensaje": f"Correo enviado a {destino} (Brevo)"}


def _enviar_resend(
    destino: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str | None,
    cfg: dict,
) -> dict:
    api_key = (cfg.get("email_resend_api_key") or "").strip()
    if not api_key:
        return {"error": "Configure la API key de Resend (email_resend_api_key)"}

    remitente, nombre = _remitente(cfg)
    if not remitente:
        return {"error": "Configure el correo remitente"}

    payload = {
        "from": f"{nombre} <{remitente}>",
        "to": [destino],
        "subject": asunto,
        "text": cuerpo_texto,
    }
    if cuerpo_html:
        payload["html"] = cuerpo_html

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            if resp.status not in (200, 201):
                return {"error": f"Resend respondió HTTP {resp.status}"}
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
            det = json.loads(body).get("message", body) if body else str(e)
        except Exception:
            det = str(e)
        return {"error": f"Resend: {det}"}
    except urllib.error.URLError as e:
        return {"error": f"No se pudo contactar a Resend: {e.reason}"}

    return {"mensaje": f"Correo enviado a {destino} (Resend)"}


def _enviar_smtp(
    destino: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str | None,
    cfg: dict,
    *,
    etiqueta: str = "SMTP",
) -> dict:
    host = (cfg.get("email_smtp_host") or "").strip()
    if not host:
        return {"error": "Configure el servidor SMTP (host)"}

    usuario = (cfg.get("email_smtp_usuario") or "").strip()
    password = cfg.get("email_smtp_password") or ""
    remitente, nombre = _remitente(cfg)
    if not remitente:
        return {"error": "Configure el correo remitente"}

    port = int(cfg.get("email_smtp_port") or 587)
    usar_tls = bool(cfg.get("email_smtp_tls", True))
    # Mailpit / local: nunca TLS
    if etiqueta == "Mailpit" or port in (1025, 1026):
        usar_tls = False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = f"{nombre} <{remitente}>"
    msg["To"] = destino
    msg.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
    if cuerpo_html:
        msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
                if usuario:
                    smtp.login(usuario, password)
                smtp.sendmail(remitente, [destino], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                if usar_tls:
                    smtp.starttls()
                if usuario:
                    smtp.login(usuario, password)
                smtp.sendmail(remitente, [destino], msg.as_string())
    except smtplib.SMTPAuthenticationError:
        if etiqueta == "Gmail" or "gmail" in host.lower():
            return {
                "error": (
                    "Google rechazó el acceso. Use una contraseña de aplicación "
                    "(no la clave normal). En cuentas @uteq.edu.ec u otras "
                    "institucionales, el admin de Google Workspace debe permitir "
                    "contraseñas de aplicaciones. Guía: myaccount.google.com/apppasswords"
                )
            }
        return {"error": "Autenticación SMTP fallida: revise usuario y contraseña"}
    except smtplib.SMTPException as e:
        return {"error": f"Error SMTP: {e}"}
    except OSError as e:
        hint = ""
        if etiqueta == "Mailpit" or port == 1025:
            hint = " ¿Mailpit está corriendo? (docker run -d -p 1025:1025 -p 8025:8025 axllent/mailpit)"
        return {"error": f"No se pudo conectar al servidor SMTP: {e}.{hint}"}

    extra = " — ábralo en http://127.0.0.1:8025" if etiqueta == "Mailpit" else ""
    return {"mensaje": f"Correo enviado a {destino} ({etiqueta}){extra}"}


def enviar_correo(
    destino: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str | None = None,
    *,
    plantilla: str | None = None,
) -> dict:
    cfg = _cfg()
    if plantilla and not plantilla_habilitada(plantilla, cfg):
        return {
            "omitido": True,
            "mensaje": f"Plantilla «{plantilla}» desactivada en Configuración → Correo",
        }
    if not cfg.get("email"):
        return {
            "error": (
                "El envío de correo está deshabilitado. "
                "Vaya a Gobierno → Configuración → Correo y actívelo."
            )
        }

    destino = (destino or "").strip()
    if not destino:
        return {"error": "Indique un destinatario"}

    proveedor = (cfg.get("email_proveedor") or "gmail").strip().lower()
    if proveedor == "brevo":
        return _enviar_brevo(destino, asunto, cuerpo_texto, cuerpo_html, cfg)
    if proveedor == "resend":
        return _enviar_resend(destino, asunto, cuerpo_texto, cuerpo_html, cfg)
    if proveedor == "gmail":
        gmail = str(cfg.get("email_smtp_usuario") or cfg.get("email_remitente") or "").strip()
        cfg_g = {
            **cfg,
            "email_smtp_host": "smtp.gmail.com",
            "email_smtp_port": int(cfg.get("email_smtp_port") or 587),
            "email_smtp_tls": True,
            "email_smtp_usuario": gmail,
            "email_remitente": (cfg.get("email_remitente") or gmail).strip(),
        }
        if not cfg_g["email_smtp_usuario"]:
            return {"error": "Indique su Gmail como usuario SMTP"}
        if not (cfg_g.get("email_smtp_password") or "").strip():
            return {
                "error": (
                    "Falta la contraseña de aplicación de Google. "
                    "Cree una en https://myaccount.google.com/apppasswords "
                    "(no use su clave normal de Gmail)."
                )
            }
        return _enviar_smtp(destino, asunto, cuerpo_texto, cuerpo_html, cfg_g, etiqueta="Gmail")
    if proveedor == "mailpit":
        cfg_mp = {**cfg, **{k: v for k, v in PRESETS["mailpit"].items() if k.startswith("email_smtp") or k == "email_remitente"}}
        if not (cfg.get("email_smtp_host") or "").strip():
            cfg_mp["email_smtp_host"] = "127.0.0.1"
        if not cfg.get("email_smtp_port"):
            cfg_mp["email_smtp_port"] = 1025
        cfg_mp["email_smtp_tls"] = False
        return _enviar_smtp(destino, asunto, cuerpo_texto, cuerpo_html, cfg_mp, etiqueta="Mailpit")
    return _enviar_smtp(destino, asunto, cuerpo_texto, cuerpo_html, cfg)


def probar_envio(destino: str | None = None) -> dict:
    cfg = _cfg()
    dest = (destino or cfg.get("email_destino_prueba") or cfg.get("email_destino_alertas") or cfg.get("email_smtp_usuario") or "").strip()
    if not dest:
        return {"error": "Indique un correo de prueba o configure destino de alertas"}

    from paquetes.configuracion.ConfiguracionEmailPlantillas import (
        asunto_plantilla,
        render_plantilla,
    )

    texto, html = render_plantilla("prueba")
    return enviar_correo(dest, asunto_plantilla("prueba"), texto, html, plantilla="prueba")



def aplicar_preset_mailpit(usuario: str = "sistema") -> dict:
    from paquetes.configuracion.ConfiguracionServicio import guardar_configuracion
    return guardar_configuracion(dict(PRESETS["mailpit"]), usuario)


def aplicar_preset_gmail(usuario: str = "sistema", gmail: str = "") -> dict:
    from paquetes.configuracion.ConfiguracionServicio import (
        guardar_configuracion,
        obtener_configuracion,
    )
    actual = obtener_configuracion(enmascarar_secretos=False)
    datos = dict(PRESETS["gmail"])
    # No borrar contraseña ya guardada
    if actual.get("email_smtp_password"):
        datos.pop("email_smtp_password", None)
    gmail = (gmail or "").strip()
    if gmail:
        datos["email_smtp_usuario"] = gmail
        datos["email_remitente"] = gmail
        datos["email_destino_alertas"] = gmail
    return guardar_configuracion(datos, usuario)
