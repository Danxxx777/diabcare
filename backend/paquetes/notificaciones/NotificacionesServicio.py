"""
NotificacionesServicio — P10 Notificaciones dirigidas (in-app + email).
Pacientes: canal email (sin portal en esta fase).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pandas as pd

from nucleo.utilidades.ParquetCache import leer, escribir
from nucleo.utilidades.LogConfig import log_advertencia

BUCKET_APP = "diabcare-app"
ARCHIVO = "notificaciones/alertas.parquet"
COLUMNAS = [
    "id", "titulo", "mensaje", "tipo", "leida", "creado_en", "email_enviado",
    "destinatario_tipo", "destinatario", "canal", "referencia_tipo", "referencia_id",
]

UMBRAL_HBA1C = 7.5
UMBRAL_GLUCOSA = 180
TIPOS_EMAIL = {"warning", "error", "critico", "critical", "alerta"}


def _extraer() -> pd.DataFrame:
    return leer(BUCKET_APP, ARCHIVO, COLUMNAS)


def _cargar(df: pd.DataFrame) -> None:
    for col in COLUMNAS:
        if col not in df.columns:
            df[col] = False if col in ("leida", "email_enviado") else ""
    escribir(BUCKET_APP, ARCHIVO, df[COLUMNAS])


def _enviar_email_alerta(
    titulo: str,
    mensaje: str,
    destino: str | None = None,
    *,
    plantilla: str = "alerta",
    referencia_id: str = "",
) -> bool:
    try:
        from paquetes.configuracion.ConfiguracionEmailServicio import enviar_correo
        from paquetes.configuracion.ConfiguracionEmailPlantillas import (
            asunto_plantilla,
            render_plantilla,
        )
        from paquetes.configuracion.ConfiguracionServicio import obtener_configuracion

        cfg = obtener_configuracion(enmascarar_secretos=False)
        dest = (destino or cfg.get("email_destino_alertas") or "").strip()
        if not dest:
            return False
        if not cfg.get("email"):
            return False
        cat = (plantilla or "alerta").lower()
        texto, html = render_plantilla(
            cat,
            titulo=titulo,
            mensaje=mensaje,
            referencia_id=referencia_id,
        )
        r = enviar_correo(dest, asunto_plantilla(cat, titulo=titulo), texto, html, plantilla=cat)
        return "error" not in r and not r.get("omitido")
    except Exception as e:
        log_advertencia(f"Notificaciones: fallo envío email: {e}")
        return False


def enviar_correo_usuario(
    destino: str,
    asunto: str,
    cuerpo: str,
    *,
    plantilla: str = "notificacion",
    **ctx,
) -> dict:
    from paquetes.configuracion.ConfiguracionEmailServicio import enviar_correo
    from paquetes.configuracion.ConfiguracionEmailPlantillas import render_plantilla

    texto, html = render_plantilla(
        plantilla,
        titulo=asunto.replace("DiabCare — ", "").strip() or "Aviso",
        mensaje=cuerpo,
        cuerpo=cuerpo,
        **ctx,
    )
    return enviar_correo(destino, asunto, texto, html, plantilla=plantilla)


def emitir(
    titulo: str,
    mensaje: str,
    tipo: str = "info",
    *,
    destinatario_tipo: str = "todos",
    destinatario: str = "",
    canal: str = "in_app",
    referencia_tipo: str = "",
    referencia_id: str = "",
    destino_email: str | None = None,
) -> dict:
    """
    Emite notificación dirigida.
    destinatario_tipo: usuario | rol | paciente_email | todos
    canal: in_app | email | ambos
    """
    df = _extraer()
    tipo = (tipo or "info").lower()
    destinatario_tipo = (destinatario_tipo or "todos").lower()
    canal = (canal or "in_app").lower()
    email_ok = False

    email_destino = destino_email
    if not email_destino and destinatario_tipo == "paciente_email":
        email_destino = destinatario
    if not email_destino and destinatario_tipo == "usuario" and destinatario:
        try:
            from paquetes.usuarios.UsuariosServicio import obtener_usuario
            u = obtener_usuario(destinatario)
            if "error" not in u:
                email_destino = u.get("email")
        except Exception:
            pass

    plantilla = "factura" if (referencia_tipo or "").lower() == "factura" else (
        "alerta" if tipo in TIPOS_EMAIL else "notificacion"
    )

    if canal in ("email", "ambos") or (tipo in TIPOS_EMAIL and canal != "in_app"):
        email_ok = _enviar_email_alerta(
            titulo, mensaje, email_destino,
            plantilla=plantilla, referencia_id=str(referencia_id or ""),
        )
    elif canal == "in_app" and tipo in TIPOS_EMAIL and destinatario_tipo in ("todos", "rol"):
        # fallback histórico: alertas clínicas a email_destino_alertas
        email_ok = _enviar_email_alerta(
            titulo, mensaje, None,
            plantilla=plantilla, referencia_id=str(referencia_id or ""),
        )

    # Paciente sin portal: no crear fila in-app visible a staff salvo que canal sea ambos/in_app para roles
    crear_in_app = canal in ("in_app", "ambos") and destinatario_tipo != "paciente_email"
    if destinatario_tipo == "paciente_email" and canal == "email":
        crear_in_app = False
        # Guardamos registro para auditoría de envíos
        crear_in_app = True  # keep history; filtered out for staff inbox unless admin
        destinatario_tipo = "paciente_email"

    fila = {
        "id": str(uuid.uuid4()),
        "titulo": str(titulo or "Notificación"),
        "mensaje": str(mensaje or ""),
        "tipo": tipo,
        "leida": False if crear_in_app else True,
        "creado_en": datetime.now().isoformat(),
        "email_enviado": email_ok,
        "destinatario_tipo": destinatario_tipo,
        "destinatario": str(destinatario or ""),
        "canal": canal,
        "referencia_tipo": str(referencia_tipo or ""),
        "referencia_id": str(referencia_id or ""),
    }
    _cargar(pd.concat([df, pd.DataFrame([fila])], ignore_index=True))
    return fila


def crear(
    titulo: str,
    mensaje: str,
    tipo: str = "info",
    enviar_email: bool | None = None,
    destino_email: str | None = None,
) -> dict:
    """Compat: notificación global in-app (+ email umbral)."""
    tipo = (tipo or "info").lower()
    if enviar_email is None:
        enviar_email = tipo in TIPOS_EMAIL
    canal = "ambos" if enviar_email else "in_app"
    return emitir(
        titulo, mensaje, tipo,
        destinatario_tipo="todos",
        destinatario="",
        canal=canal,
        destino_email=destino_email,
    )


def _visible_para(row, user_id: str, rol: str, es_admin: bool) -> bool:
    tipo_d = str(row.get("destinatario_tipo") or "todos").lower()
    dest = str(row.get("destinatario") or "")
    if tipo_d == "paciente_email":
        return es_admin  # historial solo admin
    if tipo_d == "todos" or tipo_d == "":
        return True
    if tipo_d == "rol":
        return dest.lower() == str(rol).lower() or es_admin
    if tipo_d == "usuario":
        return dest == str(user_id) or es_admin
    return es_admin


def listar(
    skip: int = 0,
    limit: int = 50,
    solo_no_leidas: bool = False,
    *,
    user_id: str = "",
    rol: str = "",
) -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "no_leidas": 0, "notificaciones": []}

    es_admin = rol == "administrador"
    if user_id or rol:
        # Vectorizado aproximado (más rápido que apply fila a fila)
        tipo_d = df.get("destinatario_tipo", pd.Series([""] * len(df))).astype(str).str.lower()
        dest = df.get("destinatario", pd.Series([""] * len(df))).astype(str)
        mask = (
            tipo_d.isin(["todos", ""])
            | ((tipo_d == "rol") & ((dest.str.lower() == str(rol).lower()) | es_admin))
            | ((tipo_d == "usuario") & ((dest == str(user_id)) | es_admin))
            | ((tipo_d == "paciente_email") & es_admin)
        )
        df = df[mask]

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


def marcar_leida(notif_id: str, user_id: str = "", rol: str = "") -> dict:
    df = _extraer()
    idx = df.index[df["id"] == notif_id].tolist()
    if not idx:
        return {"error": "Notificación no encontrada"}
    row = df.loc[idx[0]]
    if user_id and not _visible_para(row, user_id, rol, rol == "administrador"):
        return {"error": "Notificación no encontrada"}
    df.at[idx[0], "leida"] = True
    _cargar(df)
    return {"mensaje": "Marcada como leída"}


def marcar_todas_leidas(user_id: str = "", rol: str = "") -> dict:
    df = _extraer()
    if df.empty:
        return {"mensaje": "Sin notificaciones"}
    es_admin = rol == "administrador"
    for i, row in df.iterrows():
        if _visible_para(row, user_id, rol, es_admin):
            df.at[i, "leida"] = True
    _cargar(df)
    return {"mensaje": "Todas marcadas como leídas"}


def estadisticas(user_id: str = "", rol: str = "") -> dict:
    data = listar(limit=500, user_id=user_id, rol=rol)
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
        email_pac = str(row.get("email") or row.get("paciente_email") or "").strip()

        if hba1c > UMBRAL_HBA1C:
            titulo = f"Alerta HbA1c — encuentro {eid}"
            if not _ya_existe_titulo_reciente(titulo):
                emitir(
                    titulo,
                    f"{paciente}: HbA1c {hba1c:.1f}% supera umbral {UMBRAL_HBA1C}%.",
                    "warning",
                    destinatario_tipo="rol",
                    destinatario="medico",
                    canal="ambos",
                    referencia_tipo="encuentro",
                    referencia_id=str(eid),
                )
                if email_pac:
                    emitir(
                        "DiabCare — Resultado de seguimiento",
                        f"Hola {paciente}, su HbA1c ({hba1c:.1f}%) requiere seguimiento. Contacte a su médico.",
                        "info",
                        destinatario_tipo="paciente_email",
                        destinatario=email_pac,
                        canal="email",
                        destino_email=email_pac,
                    )
                nuevas += 1

        if glucosa > UMBRAL_GLUCOSA:
            titulo = f"Alerta glucosa — encuentro {eid}"
            if not _ya_existe_titulo_reciente(titulo):
                emitir(
                    titulo,
                    f"{paciente}: glucosa {glucosa:.0f} mg/dL supera umbral {UMBRAL_GLUCOSA}.",
                    "warning",
                    destinatario_tipo="rol",
                    destinatario="medico",
                    canal="ambos",
                    referencia_tipo="encuentro",
                    referencia_id=str(eid),
                )
                nuevas += 1

    return {"evaluadas": int(len(df)), "alertas_nuevas": nuevas}
