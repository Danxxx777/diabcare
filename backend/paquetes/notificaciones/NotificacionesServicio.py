"""
NotificacionesServicio — P10 Notificaciones y alertas clínicas.

Persiste alertas en MinIO (Parquet) y envía correo vía Brevo/SMTP configurado en P12.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta

import pandas as pd

from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
from nucleo.utilidades.LogConfig import log_advertencia

BUCKET_APP = "diabcare-app"
ARCHIVO = "notificaciones/alertas.parquet"
COLUMNAS = ["id", "titulo", "mensaje", "tipo", "leida", "creado_en", "email_enviado"]

UMBRAL_HBA1C = 7.5
UMBRAL_GLUCOSA = 180
TIPOS_EMAIL = {"warning", "error", "critico", "critical", "alerta"}


def _extraer() -> pd.DataFrame:
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)


def _cargar(df: pd.DataFrame) -> None:
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, ARCHIVO, buf, buf.getbuffer().nbytes)


def _enviar_email_alerta(titulo: str, mensaje: str, destino: str | None = None) -> bool:
    try:
        from paquetes.configuracion.ConfiguracionEmailServicio import enviar_correo
        from paquetes.configuracion.ConfiguracionServicio import obtener_configuracion

        cfg = obtener_configuracion(enmascarar_secretos=False)
        dest = (destino or cfg.get("email_destino_alertas") or "").strip()
        if not dest:
            return False
        html = (
            f"<h2>{titulo}</h2><p>{mensaje}</p>"
            "<hr><p style='font-size:12px;color:#666'>DiabCare Analytics — alerta automática</p>"
        )
        r = enviar_correo(dest, f"DiabCare — {titulo}", mensaje, html)
        return "error" not in r
    except Exception as e:
        log_advertencia(f"Notificaciones: fallo envío email: {e}")
        return False


def enviar_correo_usuario(destino: str, asunto: str, cuerpo: str) -> dict:
    """Envío directo (p. ej. recuperación de contraseña)."""
    from paquetes.configuracion.ConfiguracionEmailServicio import enviar_correo

    html = f"<p>{cuerpo.replace(chr(10), '<br>')}</p>"
    return enviar_correo(destino, asunto, cuerpo, html)


def crear(
    titulo: str,
    mensaje: str,
    tipo: str = "info",
    enviar_email: bool | None = None,
    destino_email: str | None = None,
) -> dict:
    """Crea una notificación in-app y opcionalmente envía correo."""
    df = _extraer()
    tipo = (tipo or "info").lower()
    if enviar_email is None:
        enviar_email = tipo in TIPOS_EMAIL

    email_ok = False
    if enviar_email:
        email_ok = _enviar_email_alerta(titulo, mensaje, destino_email)

    fila = {
        "id": str(uuid.uuid4()),
        "titulo": str(titulo or "Notificación"),
        "mensaje": str(mensaje or ""),
        "tipo": tipo,
        "leida": False,
        "creado_en": datetime.now().isoformat(),
        "email_enviado": email_ok,
    }
    _cargar(pd.concat([df, pd.DataFrame([fila])], ignore_index=True))
    return fila


def listar(skip: int = 0, limit: int = 50, solo_no_leidas: bool = False) -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "no_leidas": 0, "notificaciones": []}
    if solo_no_leidas and "leida" in df.columns:
        df = df[df["leida"] != True]  # noqa: E712
    df = df.sort_values("creado_en", ascending=False)
    total = int(len(df))
    no_leidas = int((df["leida"] != True).sum()) if "leida" in df.columns else 0  # noqa: E712
    pagina = df.iloc[skip: skip + limit]
    return {
        "total": total,
        "no_leidas": no_leidas,
        "notificaciones": pagina.fillna("").to_dict(orient="records"),
    }


def marcar_leida(notif_id: str) -> dict:
    df = _extraer()
    idx = df.index[df["id"] == notif_id].tolist()
    if not idx:
        return {"error": "Notificación no encontrada"}
    df.at[idx[0], "leida"] = True
    _cargar(df)
    return {"mensaje": "Marcada como leída"}


def marcar_todas_leidas() -> dict:
    df = _extraer()
    if df.empty:
        return {"mensaje": "Sin notificaciones"}
    df["leida"] = True
    _cargar(df)
    return {"mensaje": "Todas marcadas como leídas"}


def estadisticas() -> dict:
    data = listar(limit=500)
    notifs = data["notificaciones"]
    hoy = datetime.now().date().isoformat()
    alertas_hoy = sum(1 for n in notifs if str(n.get("creado_en", "")).startswith(hoy))
    criticas = sum(1 for n in notifs if n.get("tipo") in TIPOS_EMAIL)
    return {
        "total": data["total"],
        "no_leidas": data["no_leidas"],
        "alertas_hoy": alertas_hoy,
        "criticas": criticas,
        "emails_enviados": sum(1 for n in notifs if n.get("email_enviado")),
    }


def _ya_existe_titulo_reciente(titulo: str, horas: int = 24) -> bool:
    df = _extraer()
    if df.empty:
        return False
    limite = datetime.now() - timedelta(hours=horas)
    for _, row in df.iterrows():
        if row.get("titulo") != titulo:
            continue
        try:
            ts = datetime.fromisoformat(str(row.get("creado_en", "")))
            if ts >= limite:
                return True
        except ValueError:
            pass
    return False


def evaluar_alertas_clinicas() -> dict:
    """
    Evalúa umbrales clínicos (RN-O-005) sobre el dataset principal y crea alertas.
    HbA1c > 7.5 % o glucosa > 180 mg/dL.
    """
    try:
        from paquetes.registros_clinicos.RegistrosClinicosServicio import _extraer
    except Exception:
        return {"evaluadas": 0, "alertas_nuevas": 0}

    df = _extraer()
    if df.empty:
        return {"evaluadas": 0, "alertas_nuevas": 0}

    nuevas = 0
    for _, row in df.iterrows():
        eid = row.get("encounter_id", "?")
        hba1c = float(row.get("hbA1c_level") or 0)
        glucosa = float(row.get("blood_glucose_level") or 0)
        paciente = row.get("paciente_nombre") or row.get("id_paciente") or "Paciente"

        if hba1c > UMBRAL_HBA1C:
            titulo = f"Alerta HbA1c — encuentro {eid}"
            if not _ya_existe_titulo_reciente(titulo):
                crear(
                    titulo,
                    f"{paciente}: HbA1c {hba1c:.1f}% supera umbral {UMBRAL_HBA1C}%.",
                    "warning",
                    enviar_email=True,
                )
                nuevas += 1

        if glucosa > UMBRAL_GLUCOSA:
            titulo = f"Alerta glucosa — encuentro {eid}"
            if not _ya_existe_titulo_reciente(titulo):
                crear(
                    titulo,
                    f"{paciente}: glucosa {glucosa:.0f} mg/dL supera umbral {UMBRAL_GLUCOSA}.",
                    "warning",
                    enviar_email=True,
                )
                nuevas += 1

    return {"evaluadas": int(len(df)), "alertas_nuevas": nuevas}
