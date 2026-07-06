"""
Envío de correo vía Brevo (API REST) o SMTP según ajustes en ConfiguracionServicio.
"""

from __future__ import annotations

import json
import smtplib
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from paquetes.configuracion.ConfiguracionServicio import obtener_configuracion


def _cfg() -> dict:
    return obtener_configuracion(enmascarar_secretos=False)


def _remitente(cfg: dict) -> tuple[str, str]:
    usuario = (cfg.get("email_smtp_usuario") or "").strip()
    remitente = (cfg.get("email_remitente") or usuario).strip()
    nombre = (cfg.get("email_remitente_nombre") or "DiabCare Analytics").strip()
    return remitente, nombre


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


def _enviar_smtp(
    destino: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str | None,
    cfg: dict,
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
        return {"error": "Autenticación SMTP fallida: revise usuario y contraseña"}
    except smtplib.SMTPException as e:
        return {"error": f"Error SMTP: {e}"}
    except OSError as e:
        return {"error": f"No se pudo conectar al servidor SMTP: {e}"}

    return {"mensaje": f"Correo enviado a {destino}"}


def enviar_correo(
    destino: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str | None = None,
) -> dict:
    cfg = _cfg()
    if not cfg.get("email"):
        return {"error": "El envío de correo está deshabilitado en configuración"}

    destino = (destino or "").strip()
    if not destino:
        return {"error": "Indique un destinatario"}

    proveedor = (cfg.get("email_proveedor") or "brevo").strip().lower()
    if proveedor == "brevo":
        return _enviar_brevo(destino, asunto, cuerpo_texto, cuerpo_html, cfg)
    return _enviar_smtp(destino, asunto, cuerpo_texto, cuerpo_html, cfg)


def probar_envio(destino: str | None = None) -> dict:
    cfg = _cfg()
    dest = (destino or cfg.get("email_destino_alertas") or cfg.get("email_smtp_usuario") or "").strip()
    if not dest:
        return {"error": "Indique un correo de prueba o configure destino de alertas"}

    proveedor = (cfg.get("email_proveedor") or "brevo").strip().lower()
    texto = (
        "Este es un correo de prueba enviado desde DiabCare Analytics.\n\n"
        f"Proveedor activo: {proveedor.upper()}.\n"
        "Si lo recibió, la configuración de correo es correcta."
    )
    html = (
        "<p>Este es un <strong>correo de prueba</strong> enviado desde "
        f"<em>DiabCare Analytics</em>.</p>"
        f"<p>Proveedor activo: <strong>{proveedor.upper()}</strong>.</p>"
        "<p>Si lo recibió, la configuración es correcta.</p>"
    )
    return enviar_correo(dest, "DiabCare — Prueba de correo", texto, html)
