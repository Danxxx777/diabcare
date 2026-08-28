"""
NotificacionesServicio - P10 Notificaciones dirigidas por rol (in-app + email).

Cada aviso va a uno o más roles. La bandeja del usuario solo muestra lo de su rol
(+ avisos personales; historial paciente_email solo Administrador).

Matriz operativa (quién actúa → quién recibe):
  Recepción/Caja cobra cita     → Médico
  Admisiones registra ingreso   → Médico, Enfermero
  Laboratorio carga resultado   → Médico
  Médico emite receta           → Farmacéutico
  Farmacia stock bajo           → Farmacéutico, Administrador
  Factura emitida               → Administrador
  Solicitud de acceso           → Administrador
  Alertas HbA1c / glucosa       → Médico
  Modelo ML / reporte / dataset → Analista, Administrador
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

# Tope de alertas creadas por corrida. Materializar 50.000 registros llegaba a
# generar ~8.500 filas de golpe, inutilizando la bandeja y el tiempo de carga.
MAX_ALERTAS_POR_CORRIDA = 200
# Por encima de esto se manda un solo correo resumen en lugar de uno por alerta.
MAX_EMAILS_INDIVIDUALES = 10

ROLES_VALIDOS = ("administrador", "medico", "enfermero", "farmaceutico", "analista")

# Etiquetas con mayúscula inicial (UI / mensajes)
ETIQUETA_ROL = {
    "administrador": "Administrador",
    "medico": "Médico",
    "enfermero": "Enfermero",
    "farmaceutico": "Farmacéutico",
    "analista": "Analista",
}


def etiqueta_rol(rol: str) -> str:
    key = str(rol or "").strip().lower()
    return ETIQUETA_ROL.get(key) or (key[:1].upper() + key[1:] if key else "")


def _normalizar_roles(roles) -> list[str]:
    if roles is None:
        return []
    if isinstance(roles, str):
        parts = [p.strip().lower() for p in roles.replace(";", ",").split(",")]
    else:
        parts = [str(p).strip().lower() for p in roles]
    out = []
    for p in parts:
        if p in ROLES_VALIDOS and p not in out:
            out.append(p)
    return out


def _roles_en_destinatario(dest: str) -> list[str]:
    return _normalizar_roles(dest)


def _extraer() -> pd.DataFrame:
    return leer(BUCKET_APP, ARCHIVO, COLUMNAS)


def _cargar(df: pd.DataFrame) -> None:
    for col in COLUMNAS:
        if col not in df.columns:
            df[col] = False if col in ("leida", "email_enviado") else ""
    df = _podar(df)
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
        titulo=asunto.replace("DiabCare - ", "").strip() or "Aviso",
        mensaje=cuerpo,
        cuerpo=cuerpo,
        **ctx,
    )
    return enviar_correo(destino, asunto, texto, html, plantilla=plantilla)


def _fila_notificacion(
    titulo: str,
    mensaje: str,
    tipo: str = "info",
    *,
    leida: bool = False,
    email_enviado: bool = False,
    destinatario_tipo: str = "todos",
    destinatario: str = "",
    canal: str = "in_app",
    referencia_tipo: str = "",
    referencia_id: str = "",
) -> dict:
    """Construye una fila de notificación sin tocar MinIO (permite insertar en lote)."""
    return {
        "id": str(uuid.uuid4()),
        "titulo": str(titulo or "Notificación"),
        "mensaje": str(mensaje or ""),
        "tipo": (tipo or "info").lower(),
        "leida": bool(leida),
        "creado_en": datetime.now().isoformat(),
        "email_enviado": bool(email_enviado),
        "destinatario_tipo": (destinatario_tipo or "todos").lower(),
        "destinatario": str(destinatario or ""),
        "canal": (canal or "in_app").lower(),
        "referencia_tipo": str(referencia_tipo or ""),
        "referencia_id": str(referencia_id or ""),
    }


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

    fila = _fila_notificacion(
        titulo, mensaje, tipo,
        leida=not crear_in_app,
        email_enviado=email_ok,
        destinatario_tipo=destinatario_tipo,
        destinatario=destinatario,
        canal=canal,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
    )
    _cargar(pd.concat([df, pd.DataFrame([fila])], ignore_index=True))
    return fila


def emitir_a_roles(
    titulo: str,
    mensaje: str,
    tipo: str = "info",
    roles: list[str] | str | None = None,
    *,
    canal: str = "in_app",
    referencia_tipo: str = "",
    referencia_id: str = "",
    destino_email: str | None = None,
) -> list[dict]:
    """Crea una notificación in-app por cada rol destino."""
    lista = _normalizar_roles(roles)
    if not lista:
        return []
    out = []
    for rol in lista:
        out.append(emitir(
            titulo,
            mensaje,
            tipo,
            destinatario_tipo="rol",
            destinatario=rol,
            canal=canal,
            referencia_tipo=referencia_tipo,
            referencia_id=referencia_id,
            destino_email=destino_email,
        ))
    return out


def crear(
    titulo,
    mensaje: str = "",
    tipo: str = "info",
    enviar_email: bool | None = None,
    destino_email: str | None = None,
    roles=None,
    rol: str | None = None,
) -> dict | list:
    """
    Compat: si `titulo` es dict (llamadas antiguas), lee campos de ahí.
    Preferir `roles=[...]` - ya no se usa destinatario 'todos' por defecto.
    """
    if isinstance(titulo, dict):
        d = titulo
        return crear(
            d.get("titulo", "Aviso"),
            d.get("mensaje", ""),
            d.get("tipo", "info"),
            enviar_email=d.get("enviar_email"),
            destino_email=d.get("destino_email"),
            roles=d.get("roles") or d.get("rol"),
        )

    tipo = (tipo or "info").lower()
    if enviar_email is None:
        enviar_email = tipo in TIPOS_EMAIL
    canal = "ambos" if enviar_email else "in_app"
    dest_roles = _normalizar_roles(roles if roles is not None else rol)
    if not dest_roles:
        # Sin rol explícito: solo Administrador (evita broadcast a todos)
        dest_roles = ["administrador"]
    filas = emitir_a_roles(
        str(titulo), str(mensaje or ""), tipo,
        roles=dest_roles, canal=canal, destino_email=destino_email,
    )
    return filas[0] if len(filas) == 1 else filas


def _visible_para(row, user_id: str, rol: str, es_admin: bool) -> bool:
    tipo_d = str(row.get("destinatario_tipo") or "todos").lower()
    dest = str(row.get("destinatario") or "")
    rol_u = str(rol or "").lower()
    if tipo_d == "paciente_email":
        return es_admin  # historial solo Administrador
    if tipo_d == "todos" or tipo_d == "":
        return True
    if tipo_d == "rol":
        return rol_u in _roles_en_destinatario(dest)
    if tipo_d == "usuario":
        return dest == str(user_id)
    return False


def _enriquecer_fila(n: dict) -> dict:
    tipo_d = str(n.get("destinatario_tipo") or "")
    dest = str(n.get("destinatario") or "")
    if tipo_d == "rol":
        labels = [etiqueta_rol(r) for r in _roles_en_destinatario(dest)]
        n["destinatario_label"] = ", ".join(labels) if labels else etiqueta_rol(dest)
    elif tipo_d == "todos":
        n["destinatario_label"] = "Todos"
    elif tipo_d == "paciente_email":
        n["destinatario_label"] = "Paciente"
    elif tipo_d == "usuario":
        n["destinatario_label"] = "Usuario"
    else:
        n["destinatario_label"] = dest or "-"
    return n


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

    es_admin = str(rol).lower() == "administrador"
    rol_u = str(rol or "").lower()
    if user_id or rol:
        tipo_d = df.get("destinatario_tipo", pd.Series([""] * len(df))).astype(str).str.lower()
        dest = df.get("destinatario", pd.Series([""] * len(df))).astype(str)
        # Solo el propio rol (sin filtrar “todo lo del admin”)
        rol_match = dest.map(lambda d: rol_u in _roles_en_destinatario(d))
        mask = (
            tipo_d.isin(["todos", ""])
            | ((tipo_d == "rol") & rol_match)
            | ((tipo_d == "usuario") & (dest == str(user_id)))
            | ((tipo_d == "paciente_email") & es_admin)
        )
        df = df[mask]

    if solo_no_leidas and "leida" in df.columns:
        df = df[df["leida"] != True]  # noqa: E712
    df = df.sort_values("creado_en", ascending=False)
    total = int(len(df))
    no_leidas = int((df["leida"] != True).sum()) if "leida" in df.columns else 0  # noqa: E712
    pagina = df.iloc[skip: skip + limit]
    notifs = [_enriquecer_fila(r) for r in pagina.fillna("").to_dict(orient="records")]
    return {
        "total": total,
        "no_leidas": no_leidas,
        "notificaciones": notifs,
        "rol": rol_u,
        "rol_label": etiqueta_rol(rol_u),
    }


def marcar_leida(notif_id: str, user_id: str = "", rol: str = "") -> dict:
    df = _extraer()
    idx = df.index[df["id"] == notif_id].tolist()
    if not idx:
        return {"error": "Notificación no encontrada"}
    row = df.loc[idx[0]]
    if user_id and not _visible_para(row, user_id, rol, str(rol).lower() == "administrador"):
        return {"error": "Notificación no encontrada"}
    df.at[idx[0], "leida"] = True
    _cargar(df)
    return {"mensaje": "Marcada como leída"}


def marcar_todas_leidas(user_id: str = "", rol: str = "") -> dict:
    df = _extraer()
    if df.empty:
        return {"mensaje": "Sin notificaciones"}
    es_admin = str(rol).lower() == "administrador"
    for i, row in df.iterrows():
        if _visible_para(row, user_id, rol, es_admin):
            df.at[i, "leida"] = True
    _cargar(df)
    return {"mensaje": "Todas marcadas como leídas"}


# Tope de la bandeja. Por encima de esto se descartan las leidas mas viejas:
# 12 000 avisos acumulados no le sirven a nadie y ralentizan cada carga.
MAX_NOTIFICACIONES = 2000


def _podar(df: pd.DataFrame) -> pd.DataFrame:
    """Recorta la bandeja al tope, sacrificando primero las leidas mas viejas."""
    if len(df) <= MAX_NOTIFICACIONES:
        return df
    orden = df.sort_values("creado_en", ascending=False)
    leidas = orden["leida"].fillna(False).astype(bool) if "leida" in orden.columns else False
    no_leidas = orden[~leidas]
    resto = orden[leidas]
    cupo = max(0, MAX_NOTIFICACIONES - len(no_leidas))
    return pd.concat([no_leidas, resto.head(cupo)], ignore_index=True)


def purgar_leidas(user_id: str = "", rol: str = "", dias: int = 0) -> dict:
    """Elimina las notificaciones ya leidas visibles para el usuario.

    Con `dias`, conserva las leidas mas recientes que ese umbral.
    """
    df = _extraer()
    if df.empty:
        return {"mensaje": "Sin notificaciones", "eliminadas": 0}
    es_admin = str(rol).lower() == "administrador"
    corte = ""
    if dias and int(dias) > 0:
        corte = (datetime.now() - timedelta(days=int(dias))).isoformat()

    conservar = []
    eliminadas = 0
    for _, row in df.iterrows():
        leida = bool(row.get("leida"))
        visible = _visible_para(row, user_id, rol, es_admin)
        reciente = bool(corte) and str(row.get("creado_en") or "") >= corte
        if leida and visible and not reciente:
            eliminadas += 1
            continue
        conservar.append(row)

    if not eliminadas:
        return {"mensaje": "No hay notificaciones leídas para eliminar", "eliminadas": 0}
    nuevo = pd.DataFrame(conservar, columns=df.columns) if conservar else pd.DataFrame(columns=COLUMNAS)
    _cargar(nuevo)
    return {"mensaje": f"{eliminadas} notificación(es) eliminada(s)", "eliminadas": eliminadas}


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


def _titulos_recientes(horas: int = 24) -> set[str]:
    """
    Títulos emitidos en las últimas `horas`, en un único barrido vectorizado.

    Devolver un set permite deduplicar N alertas con una sola lectura. La versión
    fila a fila costaba ~900 ms por consulta con 8.000 notificaciones acumuladas.
    """
    df = _extraer()
    if df.empty or "titulo" not in df.columns:
        return set()
    ts = pd.to_datetime(df.get("creado_en"), errors="coerce")
    frescas = df.loc[ts >= (datetime.now() - timedelta(hours=horas)), "titulo"]
    return set(frescas.astype(str))


def _ya_existe_titulo_reciente(titulo: str, horas: int = 24) -> bool:
    return str(titulo) in _titulos_recientes(horas)


def evaluar_alertas_clinicas(limite: int = MAX_ALERTAS_POR_CORRIDA) -> dict:
    """
    Evalúa HbA1c y glucosa sobre el dataset clínico y avisa al médico.

    Filtra vectorizado, deduplica contra un set y escribe el parquet UNA sola vez.
    La versión anterior recorría el dataset con iterrows(), consultaba duplicados
    fila a fila (~900 ms cada consulta con 8.000 notificaciones acumuladas) y
    reescribía el parquet entero por alerta: ~12 min con 50.000 registros, y
    varias horas en la corrida siguiente.

    Los correos individuales solo se envían si la corrida genera pocas alertas
    (caso de una consulta puntual). En una carga masiva se manda un único
    resumen, en vez de miles de envíos SMTP.
    """
    try:
        from paquetes.registros_clinicos.RegistrosClinicosServicio import (
            _extraer as _extraer_registros,
        )
    except Exception:
        return {"evaluadas": 0, "alertas_nuevas": 0}

    df = _extraer_registros()
    if df.empty:
        return {"evaluadas": 0, "alertas_nuevas": 0}

    total = int(len(df))

    def _num(col: str) -> pd.Series:
        if col not in df.columns:
            return pd.Series(float("nan"), index=df.index, dtype="float64")
        return pd.to_numeric(df[col], errors="coerce")

    hba = _num("hbA1c_level")
    glc = _num("blood_glucose_level")
    # NaN > umbral es False, así que los faltantes quedan fuera solos.
    candidatos = df.loc[(hba > UMBRAL_HBA1C) | (glc > UMBRAL_GLUCOSA)]
    if candidatos.empty:
        return {"evaluadas": total, "alertas_nuevas": 0, "truncado": False}

    def _texto(col: str) -> list[str]:
        if col not in candidatos.columns:
            return [""] * len(candidatos)
        return candidatos[col].fillna("").astype(str).tolist()

    if "encounter_id" in candidatos.columns:
        eids = candidatos["encounter_id"].tolist()
    else:
        eids = list(range(1, len(candidatos) + 1))
    nombres = _texto("paciente_nombre")
    if not any(nombres):
        nombres = _texto("id_paciente")
    correos = _texto("email")
    if not any(correos):
        correos = _texto("paciente_email")

    vistos = _titulos_recientes()
    filas: list[dict] = []
    avisos_paciente: list[tuple[str, str, str]] = []
    truncado = False

    for eid, h, g, nombre, correo in zip(
        eids,
        hba.loc[candidatos.index].tolist(),
        glc.loc[candidatos.index].tolist(),
        nombres,
        correos,
    ):
        if len(filas) >= limite:
            truncado = True
            break
        paciente = nombre.strip() or "Paciente"

        if h > UMBRAL_HBA1C:
            titulo = f"Alerta HbA1c - encuentro {eid}"
            if titulo not in vistos:
                vistos.add(titulo)
                filas.append(_fila_notificacion(
                    titulo,
                    f"{paciente}: HbA1c {h:.1f}% supera umbral {UMBRAL_HBA1C}%.",
                    "warning",
                    destinatario_tipo="rol", destinatario="medico",
                    canal="in_app", referencia_tipo="encuentro", referencia_id=str(eid),
                ))
                if correo.strip():
                    avisos_paciente.append((correo.strip(), paciente, f"{h:.1f}"))

        if g > UMBRAL_GLUCOSA:
            titulo = f"Alerta glucosa - encuentro {eid}"
            if titulo not in vistos:
                vistos.add(titulo)
                filas.append(_fila_notificacion(
                    titulo,
                    f"{paciente}: glucosa {g:.0f} mg/dL supera umbral {UMBRAL_GLUCOSA}.",
                    "warning",
                    destinatario_tipo="rol", destinatario="medico",
                    canal="in_app", referencia_tipo="encuentro", referencia_id=str(eid),
                ))

    if not filas:
        return {"evaluadas": total, "alertas_nuevas": 0, "truncado": False}

    # Escritura única: antes era una reescritura completa del parquet por alerta.
    _cargar(pd.concat([_extraer(), pd.DataFrame(filas)], ignore_index=True))

    emails = 0
    if len(filas) <= MAX_EMAILS_INDIVIDUALES:
        for correo, paciente, valor in avisos_paciente:
            try:
                if _enviar_email_alerta(
                    "DiabCare - Resultado de seguimiento",
                    f"Hola {paciente}, su HbA1c ({valor}%) requiere seguimiento. "
                    "Contacte a su médico.",
                    correo,
                    plantilla="notificacion",
                ):
                    emails += 1
            except Exception:
                pass
    else:
        try:
            if _enviar_email_alerta(
                f"DiabCare - {len(filas)} alertas clínicas nuevas",
                f"Se detectaron {len(filas)} encuentros fuera de umbral "
                f"(HbA1c > {UMBRAL_HBA1C}% o glucosa > {UMBRAL_GLUCOSA} mg/dL) "
                f"sobre {total} registros. Revise la bandeja de notificaciones.",
                None,
                plantilla="alerta",
            ):
                emails = 1
        except Exception:
            pass

    return {
        "evaluadas": total,
        "alertas_nuevas": len(filas),
        "emails_enviados": emails,
        "truncado": truncado,
    }
