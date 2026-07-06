import io
import uuid
import hashlib
import pandas as pd
from datetime import datetime
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
from paquetes.usuarios.UsuariosServicio import _extraer as extraer_usuarios, crear_usuario_con_hash

BUCKET_APP = "diabcare-app"
ARCHIVO = "usuarios/solicitudes_acceso.parquet"
ROLES_SOLICITUD = ["analista", "medico"]
ESTADOS = ["pendiente", "aprobada", "rechazada"]


def _hash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def _extraer() -> pd.DataFrame:
    cols = [
        "id", "nombre", "email", "password_hash", "rol_solicitado",
        "motivo", "estado", "creado_en", "revisado_por", "revisado_en",
    ]
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame(columns=cols)


def _cargar(df: pd.DataFrame):
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, ARCHIVO, buf, buf.getbuffer().nbytes)


def _email_en_usuarios(email: str) -> bool:
    df = extraer_usuarios()
    return not df.empty and email in df["email"].values


def crear_solicitud(nombre: str, email: str, password: str, rol_solicitado: str, motivo: str = "") -> dict:
    email = email.strip().lower()
    nombre = nombre.strip()
    rol_solicitado = (rol_solicitado or "analista").strip().lower()
    motivo = (motivo or "").strip()

    if len(password) < 8:
        return {"error": "La contraseña debe tener al menos 8 caracteres"}
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
        "password_hash": _hash(password),
        "rol_solicitado": rol_solicitado,
        "motivo": motivo,
        "estado": "pendiente",
        "creado_en": datetime.utcnow().isoformat(),
        "revisado_por": "",
        "revisado_en": "",
    }
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return {
        "mensaje": "Solicitud enviada. Un administrador revisará tu acceso pronto.",
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

    resultado = crear_usuario_con_hash(
        fila["nombre"], fila["email"], fila["password_hash"], rol_final
    )
    if "error" in resultado:
        return resultado

    df.at[idx[0], "estado"] = "aprobada"
    df.at[idx[0], "revisado_por"] = revisado_por
    df.at[idx[0], "revisado_en"] = datetime.utcnow().isoformat()
    df.at[idx[0], "rol_solicitado"] = rol_final
    _cargar(df)
    return {"mensaje": "Solicitud aprobada. El usuario ya puede iniciar sesión.", "id_usuario": resultado.get("id")}


def rechazar_solicitud(id_solicitud: str, revisado_por: str) -> dict:
    df = _extraer()
    idx = df.index[df["id"] == id_solicitud].tolist()
    if not idx:
        return {"error": "Solicitud no encontrada"}
    if df.at[idx[0], "estado"] != "pendiente":
        return {"error": "La solicitud ya fue procesada"}

    df.at[idx[0], "estado"] = "rechazada"
    df.at[idx[0], "revisado_por"] = revisado_por
    df.at[idx[0], "revisado_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    return {"mensaje": "Solicitud rechazada"}
