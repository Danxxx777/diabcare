"""
Plantillas HTML de correo — estilo DiabCare (fondo oscuro, acento cian).
Cada categoría documenta para qué se usa el envío en la app.
"""

from __future__ import annotations

import html as html_lib
from typing import Any


# Roles del canal hospital (cuenta que envía / staff)
ROLES_CUENTA: list[dict[str, str]] = [
    {
        "id": "remitente",
        "nombre": "Remitente hospital",
        "desc": "Cuenta SMTP/Gmail del hospital que envía",
    },
    {
        "id": "alerta",
        "nombre": "Alertas staff",
        "desc": "Buzón del personal para alertas clínicas",
    },
    {
        "id": "prueba",
        "nombre": "Prueba de canal",
        "desc": "Verificación desde Configuración",
    },
]


# Catálogo de comunicaciones (audiencia = a quién va el mensaje)
# audiencia: paciente | rol | sistema
CATALOGO_CORREOS: list[dict[str, str]] = [
    {
        "id": "factura",
        "nombre": "Factura / comprobante",
        "audiencia": "paciente",
        "modulo": "facturacion / farmacia",
        "cuando": "Al emitir una factura",
        "destino": "email de la ficha del paciente",
    },
    {
        "id": "diagnostico",
        "nombre": "Respaldo de diagnóstico",
        "audiencia": "paciente",
        "modulo": "registros_clinicos / predicción",
        "cuando": "Al cerrar la revisión médica",
        "destino": "email de la ficha del paciente",
    },
    {
        "id": "notificacion",
        "nombre": "Aviso clínico al paciente",
        "audiencia": "paciente",
        "modulo": "notificaciones",
        "cuando": "emitir(…, destinatario_tipo=paciente_email)",
        "destino": "email del paciente",
    },
    {
        "id": "credenciales",
        "nombre": "Credenciales temporales",
        "audiencia": "rol",
        "modulo": "autenticacion / usuarios",
        "cuando": "Al aprobar solicitud de acceso",
        "destino": "email del usuario (médico, analista…)",
    },
    {
        "id": "recuperacion",
        "nombre": "Recuperación de contraseña",
        "audiencia": "rol",
        "modulo": "autenticacion",
        "cuando": "Reset de clave en login",
        "destino": "email de la cuenta app",
    },
    {
        "id": "alerta",
        "nombre": "Alertas clínicas al staff",
        "audiencia": "rol",
        "modulo": "notificaciones",
        "cuando": "Umbral HbA1c / glucosa u alertas críticas",
        "destino": "email_destino_alertas (Configuración)",
    },
    {
        "id": "prueba",
        "nombre": "Prueba de canal",
        "audiencia": "sistema",
        "modulo": "configuracion",
        "cuando": "Botón Guardar y probar",
        "destino": "correo de prueba del admin",
    },
]


def audiencia_label(audiencia: str) -> str:
    return {
        "paciente": "Pacientes",
        "rol": "Roles app",
        "sistema": "Sistema",
    }.get((audiencia or "").lower(), audiencia or "—")


def _esc(v: Any) -> str:
    return html_lib.escape("" if v is None else str(v))


def _marco(
    *,
    badge: str,
    titulo: str,
    intro: str,
    cuerpo_html: str,
    pie: str | None = None,
) -> str:
    """Sobre HTML compatible con clientes (tablas + estilos inline)."""
    badge_e = _esc(badge)
    titulo_e = _esc(titulo)
    intro_e = _esc(intro)
    pie_e = _esc(pie or "DiabCare Analytics · plataforma de analítica clínica")
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#030306;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#030306;padding:28px 12px;">
    <tr><td align="center">
      <table role="presentation" width="560" cellspacing="0" cellpadding="0" style="max-width:560px;width:100%;background:#0a0a10;border:1px solid rgba(255,255,255,0.08);border-radius:14px;overflow:hidden;">
        <tr>
          <td style="padding:22px 28px 12px;border-bottom:1px solid rgba(34,211,238,0.18);">
            <table role="presentation" width="100%"><tr>
              <td>
                <div style="font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#22d3ee;font-weight:700;">DiabCare</div>
                <div style="font-size:12px;color:#71717a;margin-top:2px;">Analytics</div>
              </td>
              <td align="right">
                <span style="display:inline-block;padding:5px 10px;border-radius:999px;font-size:10px;font-weight:600;color:#22d3ee;background:rgba(34,211,238,0.10);border:1px solid rgba(34,211,238,0.28);">{badge_e}</span>
              </td>
            </tr></table>
          </td>
        </tr>
        <tr>
          <td style="padding:26px 28px 8px;">
            <h1 style="margin:0 0 10px;font-size:22px;line-height:1.25;color:#f4f4f5;font-weight:700;">{titulo_e}</h1>
            <p style="margin:0 0 18px;font-size:14px;line-height:1.55;color:#a1a1aa;">{intro_e}</p>
            {cuerpo_html}
          </td>
        </tr>
        <tr>
          <td style="padding:18px 28px 24px;">
            <div style="height:1px;background:rgba(255,255,255,0.07);margin-bottom:14px;"></div>
            <p style="margin:0;font-size:11px;line-height:1.5;color:#52525b;">{pie_e}</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _caja_dato(label: str, valor: str, *, resaltar: bool = False) -> str:
    color = "#22d3ee" if resaltar else "#f4f4f5"
    peso = "700" if resaltar else "600"
    fondo = "rgba(34,211,238,0.08)" if resaltar else "rgba(255,255,255,0.03)"
    borde = "rgba(34,211,238,0.28)" if resaltar else "rgba(255,255,255,0.08)"
    return (
        f'<tr><td style="padding:10px 14px;border:1px solid {borde};background:{fondo};'
        f'border-radius:10px;margin-bottom:8px;">'
        f'<div style="font-size:10px;letter-spacing:0.08em;text-transform:uppercase;color:#71717a;margin-bottom:4px;">{_esc(label)}</div>'
        f'<div style="font-size:15px;color:{color};font-weight:{peso};font-family:Consolas,Monaco,monospace;">{_esc(valor)}</div>'
        f"</td></tr>"
        f'<tr><td style="height:8px;font-size:0;line-height:0;">&nbsp;</td></tr>'
    )


def _texto_plano(*lineas: str) -> str:
    return "\n".join(lineas)


def render_plantilla(categoria: str, **ctx: Any) -> tuple[str, str]:
    """Devuelve (texto_plano, html)."""
    cat = (categoria or "notificacion").strip().lower()

    if cat == "prueba":
        texto = _texto_plano(
            "Su configuración de correo en DiabCare funciona correctamente.",
            "",
            "Ya puede enviar credenciales, recuperaciones, facturas y alertas.",
        )
        cuerpo = (
            '<p style="margin:0 0 12px;font-size:14px;color:#a1a1aa;line-height:1.55;">'
            "La conexión con su proveedor quedó verificada. "
            "Los próximos avisos usarán este mismo canal.</p>"
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">'
            f'{_caja_dato("Estado", "Listo para enviar", resaltar=True)}'
            "</table>"
        )
        html = _marco(
            badge="Sistema",
            titulo="Correo verificado",
            intro="Prueba exitosa desde Configuración.",
            cuerpo_html=cuerpo,
        )
        return texto, html

    if cat == "credenciales":
        nombre = ctx.get("nombre") or "usuario"
        email = ctx.get("email") or ""
        rol = ctx.get("rol") or ""
        password = ctx.get("password") or ""
        texto = _texto_plano(
            f"Hola {nombre},",
            "",
            "Su solicitud de acceso a DiabCare fue aprobada.",
            f"Email: {email}",
            f"Rol: {rol}",
            f"Contraseña temporal: {password}",
            "",
            "Al iniciar sesión deberá actualizar su contraseña.",
        )
        cuerpo = (
            f'<p style="margin:0 0 16px;font-size:14px;color:#a1a1aa;">Hola <strong style="color:#f4f4f5;">{_esc(nombre)}</strong>, '
            "su acceso ya está activo. Use estos datos e inicie sesión; el sistema pedirá una nueva contraseña.</p>"
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">'
            f"{_caja_dato('Correo', email)}"
            f"{_caja_dato('Rol', rol)}"
            f"{_caja_dato('Contraseña temporal', password, resaltar=True)}"
            "</table>"
            '<p style="margin:14px 0 0;font-size:12px;color:#71717a;line-height:1.5;">'
            "Por seguridad, no reenvíe este correo. Si no solicitó el acceso, ignore el mensaje.</p>"
        )
        html = _marco(
            badge="Acceso",
            titulo="Credenciales temporales",
            intro="Su solicitud fue aprobada.",
            cuerpo_html=cuerpo,
        )
        return texto, html

    if cat == "recuperacion":
        codigo = ctx.get("codigo") or ""
        texto = _texto_plano(
            "Recibimos una solicitud para restablecer su contraseña en DiabCare.",
            "",
            f"Código de verificación: {codigo}",
            "",
            "Válido por 15 minutos. Si no lo solicitó, ignore este mensaje.",
        )
        cuerpo = (
            '<p style="margin:0 0 16px;font-size:14px;color:#a1a1aa;">Use este código en la pantalla de recuperación. Caduca en 15 minutos.</p>'
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">'
            f"{_caja_dato('Código', codigo, resaltar=True)}"
            "</table>"
        )
        html = _marco(
            badge="Acceso",
            titulo="Recuperar contraseña",
            intro="Solicitud de restablecimiento.",
            cuerpo_html=cuerpo,
        )
        return texto, html

    if cat == "factura":
        titulo_f = ctx.get("titulo") or "Su factura"
        mensaje = ctx.get("mensaje") or ""
        ref = ctx.get("referencia_id") or ""
        texto = _texto_plano(mensaje, "", f"Referencia: {ref}" if ref else "")
        cuerpo = (
            f'<p style="margin:0 0 16px;font-size:14px;color:#a1a1aa;line-height:1.55;">{_esc(mensaje)}</p>'
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">'
            + (_caja_dato("Referencia", ref) if ref else "")
            + (_caja_dato("Tipo", "Comprobante de factura", resaltar=True))
            + "</table>"
            '<p style="margin:14px 0 0;font-size:12px;color:#71717a;">Conserve este correo como respaldo.</p>'
        )
        html = _marco(
            badge="Negocio",
            titulo=titulo_f.replace("DiabCare — ", "").strip() or "Factura emitida",
            intro="Comprobante enviado desde DiabCare.",
            cuerpo_html=cuerpo,
        )
        return texto, html

    if cat == "alerta":
        titulo_a = ctx.get("titulo") or "Alerta clínica"
        mensaje = ctx.get("mensaje") or ""
        texto = _texto_plano(str(titulo_a), "", str(mensaje))
        cuerpo = (
            f'<p style="margin:0 0 16px;font-size:14px;color:#a1a1aa;line-height:1.55;">{_esc(mensaje)}</p>'
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">'
            f"{_caja_dato('Severidad', 'Revisar en DiabCare', resaltar=True)}"
            "</table>"
        )
        html = _marco(
            badge="Clínica",
            titulo=str(titulo_a),
            intro="Alerta automática del monitoreo clínico.",
            cuerpo_html=cuerpo,
        )
        return texto, html

    if cat == "diagnostico":
        nombre = ctx.get("nombre") or "paciente"
        mensaje = ctx.get("mensaje") or ctx.get("diagnostico") or ""
        ref = ctx.get("referencia_id") or ""
        texto = _texto_plano(
            f"Hola {nombre},",
            "",
            "Adjunto el respaldo de su revisión clínica en DiabCare.",
            str(mensaje),
            "",
            f"Referencia: {ref}" if ref else "",
        )
        cuerpo = (
            f'<p style="margin:0 0 16px;font-size:14px;color:#a1a1aa;">Hola <strong style="color:#f4f4f5;">{_esc(nombre)}</strong>, '
            "este es el respaldo de su revisión.</p>"
            f'<p style="margin:0 0 16px;font-size:14px;color:#a1a1aa;line-height:1.55;">{_esc(mensaje).replace(chr(10), "<br>")}</p>'
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">'
            + (_caja_dato("Referencia", ref) if ref else "")
            + _caja_dato("Tipo", "Respaldo clínico", resaltar=True)
            + "</table>"
        )
        html = _marco(
            badge="Clínica",
            titulo="Respaldo de diagnóstico",
            intro="Enviado por su equipo clínico.",
            cuerpo_html=cuerpo,
        )
        return texto, html

    # notificacion / genérico
    titulo_n = ctx.get("titulo") or "Aviso DiabCare"
    mensaje = ctx.get("mensaje") or ctx.get("cuerpo") or ""
    texto = _texto_plano(str(titulo_n), "", str(mensaje))
    cuerpo = f'<p style="margin:0;font-size:14px;color:#a1a1aa;line-height:1.55;">{_esc(mensaje).replace(chr(10), "<br>")}</p>'
    html = _marco(
        badge="Sistema",
        titulo=str(titulo_n),
        intro="Notificación de DiabCare Analytics.",
        cuerpo_html=cuerpo,
    )
    return texto, html


def asunto_plantilla(categoria: str, **ctx: Any) -> str:
    cat = (categoria or "").strip().lower()
    map_asuntos = {
        "prueba": "DiabCare — Correo verificado",
        "credenciales": "DiabCare — Acceso aprobado",
        "recuperacion": "DiabCare — Código de recuperación",
        "alerta": f"DiabCare — {ctx.get('titulo') or 'Alerta clínica'}",
        "factura": "DiabCare — Su factura",
        "diagnostico": "DiabCare — Respaldo de su revisión",
        "notificacion": f"DiabCare — {ctx.get('titulo') or 'Aviso'}",
    }
    return map_asuntos.get(cat, f"DiabCare — {ctx.get('titulo') or 'Aviso'}")
