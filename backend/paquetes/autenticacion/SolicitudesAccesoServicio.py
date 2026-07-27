import uuid
import secrets
import string
import pandas as pd
from datetime import datetime
from nucleo.utilidades.ParquetCache import leer, escribir
from paquetes.usuarios.UsuariosServicio import _extraer as extraer_usuarios, crear_usuario

BUCKET_APP = "diabcare-app"
ARCHIVO = "usuarios/solicitudes_acceso.parquet"
ROLES_SOLICITUD = ["analista", "medico"]
ESTADOS = ["pendiente", "aprobada", "rechazada"]
COLUMNAS = [
    "id", "nombre", "email", "password_hash", "rol_solicitado",
    "motivo", "estado", "creado_en", "revisado_por", "revisado_en",
]


def _password_temporal(n: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _extraer() -> pd.DataFrame:
    return leer(BUCKET_APP, ARCHIVO, COLUMNAS)


def _cargar(df: pd.DataFrame):
    escribir(BUCKET_APP, ARCHIVO, df)


def _email_en_usuarios(email: str) -> bool:
    df = extraer_usuarios()
    return not df.empty and email in df["email"].values


def _enviar_credenciales(email: str, nombre: str, password_temp: str, rol: str) -> dict:
    try:
        from paquetes.configuracion.ConfiguracionServicio import obtener_configuracion
        from paquetes.configuracion.ConfiguracionEmailPlantillas import (
            asunto_plantilla,
            render_plantilla,
        )
        from paquetes.configuracion.ConfiguracionEmailServicio import enviar_correo

        cfg = obtener_configuracion(enmascarar_secretos=False)
        if not cfg.get("email"):
            return {
                "ok": False,
                "error": "Correo deshabilitado en Configuración. Active el envío o use Mailpit.",
            }
        texto, html = render_plantilla(
            "credenciales",
            nombre=nombre,
            email=email,
            rol=rol,
            password=password_temp,
        )
        r = enviar_correo(email, asunto_plantilla("credenciales"), texto, html, plantilla="credenciales")
        if "error" in r:
            return {"ok": False, "error": r["error"]}
        return {"ok": True, "mensaje": r.get("mensaje", "enviado")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def crear_solicitud(nombre: str, email: str, rol_solicitado: str, motivo: str = "", password: str | None = None) -> dict:
    email = email.strip().lower()
    nombre = nombre.strip()
    rol_solicitado = (rol_solicitado or "analista").strip().lower()
    motivo = (motivo or "").strip()

    if len(nombre) < 2:
        return {"error": "Indique su nombre"}
    if "@" not in email:
        return {"error": "Email inválido"}
    if rol_solicitado not in ROLES_SOLICITUD:
        return {"error": f"Rol solicitado inválido. Opciones: {ROLES_SOLICITUD}"}
    if _email_en_usuarios(email):
        return {"error": "Este email ya tiene una cuenta activa"}

    df = _extraer()
    if not df.empty:
        pendiente = df[(df["email"] == email) & (df["estado"] == "pendiente")]
        if not pendiente.empty:
            return {"error": "Ya existe una solicitud pendiente para este email"}

    nuevo = {
        "id": str(uuid.uuid4()),
        "nombre": nombre,
        "email": email,
        "password_hash": "",
        "rol_solicitado": rol_solicitado,
        "motivo": motivo,
        "estado": "pendiente",
        "creado_en": datetime.utcnow().isoformat(),
        "revisado_por": "",
        "revisado_en": "",
    }
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return {
        "mensaje": "Solicitud enviada. Un administrador revisará tu acceso y te enviará las credenciales por correo.",
        "id": nuevo["id"],
    }


def listar_solicitudes(estado: str | None = None) -> list:
    df = _extraer()
    if df.empty:
        return []
    if estado and estado in ESTADOS:
        df = df[df["estado"] == estado]
    cols = ["id", "nombre", "email", "rol_solicitado", "motivo", "estado", "creado_en", "revisado_por", "revisado_en"]
    return df[cols].fillna("").sort_values("creado_en", ascending=False).to_dict(orient="records")


def aprobar_solicitud(id_solicitud: str, rol: str | None, revisado_por: str) -> dict:
    df = _extraer()
    idx = df.index[df["id"] == id_solicitud].tolist()
    if not idx:
        return {"error": "Solicitud no encontrada"}
    fila = df.loc[idx[0]]
    if fila["estado"] != "pendiente":
        return {"error": "La solicitud ya fue procesada"}

    rol_final = (rol or fila["rol_solicitado"] or "analista").strip().lower()
    if rol_final not in ROLES_SOLICITUD + ["administrador"]:
        return {"error": "Rol de aprobación inválido"}

    password_temp = _password_temporal()
    resultado = crear_usuario(
        fila["nombre"],
        fila["email"],
        password_temp,
        rol_final,
        debe_cambiar_password=True,
    )
    if "error" in resultado:
        return resultado

    envio = _enviar_credenciales(str(fila["email"]), str(fila["nombre"]), password_temp, rol_final)
    email_ok = bool(envio.get("ok"))

    df.at[idx[0], "estado"] = "aprobada"
    df.at[idx[0], "revisado_por"] = revisado_por
    df.at[idx[0], "revisado_en"] = datetime.utcnow().isoformat()
    df.at[idx[0], "rol_solicitado"] = rol_final
    _cargar(df)

    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(
            revisado_por,
            "aprobacion",
            "usuarios",
            f"Solicitud aprobada: {fila['email']} → {rol_final} (email={'ok' if email_ok else 'pendiente'})",
        )
    except Exception:
        pass

    resp = {
        "mensaje": (
            "Solicitud aprobada. Credenciales enviadas por correo."
            if email_ok
            else "Solicitud aprobada, pero el correo no se envió."
        ),
        "id_usuario": resultado.get("id"),
        "email_enviado": email_ok,
    }
    if not email_ok:
        resp["password_temp_dev"] = password_temp
        resp["email_error"] = envio.get("error") or "Correo no configurado"
    return resp


def rechazar_solicitud(id_solicitud: str, revisado_por: str) -> dict:
    df = _extraer()
    idx = df.index[df["id"] == id_solicitud].tolist()
    if not idx:
        return {"error": "Solicitud no encontrada"}
    if df.at[idx[0], "estado"] != "pendiente":
        return {"error": "La solicitud ya fue procesada"}

    email = str(df.at[idx[0], "email"])
    df.at[idx[0], "estado"] = "rechazada"
    df.at[idx[0], "revisado_por"] = revisado_por
    df.at[idx[0], "revisado_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(revisado_por, "rechazo", "usuarios", f"Solicitud rechazada: {email}")
    except Exception:
        pass
    return {"mensaje": "Solicitud rechazada"}
