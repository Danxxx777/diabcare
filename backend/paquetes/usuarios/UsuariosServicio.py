import io
import uuid
import hashlib
import pandas as pd
from datetime import datetime
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "usuarios/usuarios.parquet"

def _hash(p): return hashlib.sha256(p.encode()).hexdigest()

def _extraer() -> pd.DataFrame:
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame(columns=["id","nombre","email","password_hash","rol","activo","creado_en"])

def _cargar(df: pd.DataFrame):
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, ARCHIVO, buf, buf.getbuffer().nbytes)

def _serie_a_dict(serie) -> dict:
    """Convierte una pandas Series a dict limpio sin nan."""
    d = serie.to_dict()
    return {k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in d.items()}

def crear_usuario(nombre, email, password, rol):
    df = _extraer()
    if not df.empty and email in df["email"].values:
        return {"error": "Email ya registrado"}
    nuevo = {
        "id":            str(uuid.uuid4()),
        "nombre":        str(nombre),
        "email":         str(email),
        "password_hash": _hash(password),
        "rol":           str(rol),
        "activo":        True,
        "creado_en":     datetime.utcnow().isoformat()
    }
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return {"mensaje": "Usuario creado", "id": nuevo["id"]}

def crear_usuario_con_hash(nombre, email, password_hash, rol):
    email = str(email).strip().lower()
    df = _extraer()
    if not df.empty and email in df["email"].values:
        return {"error": "Email ya registrado"}
    nuevo = {
        "id":            str(uuid.uuid4()),
        "nombre":        str(nombre),
        "email":         email,
        "password_hash": str(password_hash),
        "rol":           str(rol),
        "activo":        True,
        "creado_en":     datetime.utcnow().isoformat()
    }
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return {"mensaje": "Usuario creado", "id": nuevo["id"]}

def obtener_usuarios():
    df = _extraer()
    if df.empty:
        return []
    return df[["id","nombre","email","rol","activo","creado_en"]].fillna("").to_dict(orient="records")


def listar_activos_por_rol(rol: str) -> list:
    df = _extraer()
    if df.empty:
        return []
    sub = df[df["rol"].astype(str).str.lower() == str(rol).lower()]
    if "activo" in sub.columns:
        sub = sub[sub["activo"].map(lambda v: v is True or str(v).lower() in ("true", "1", "yes", "si", "sí"))]
    sub = sub.sort_values("nombre", kind="stable")
    return sub[["id", "nombre", "email", "rol"]].fillna("").to_dict(orient="records")

def obtener_usuario(id_usuario):
    df = _extraer()
    fila = df[df["id"] == id_usuario]
    if fila.empty:
        return {"error": "Usuario no encontrado"}
    return fila[["id","nombre","email","rol","activo"]].fillna("").iloc[0].to_dict()

def editar_usuario(id_usuario, cambios):
    df = _extraer()
    idx = df.index[df["id"] == id_usuario].tolist()
    if not idx:
        return {"error": "Usuario no encontrado"}
    for k, v in cambios.items():
        if k != "password_hash":
            df.at[idx[0], k] = v
    _cargar(df)
    return {"mensaje": "Usuario actualizado"}

def desactivar_usuario(id_usuario):
    df = _extraer()
    idx = df.index[df["id"] == id_usuario].tolist()
    if not idx:
        return {"error": "Usuario no encontrado"}
    df.at[idx[0], "activo"] = False
    _cargar(df)
    return {"mensaje": "Usuario desactivado"}

def asignar_rol(id_usuario, rol):
    df = _extraer()
    idx = df.index[df["id"] == id_usuario].tolist()
    if not idx:
        return {"error": "Usuario no encontrado"}
    df.at[idx[0], "rol"] = str(rol)
    _cargar(df)
    return {"mensaje": f"Rol {rol} asignado"}

def verificar_credenciales(email, password):
    df = _extraer()
    if df.empty:
        return None
    fila = df[(df["email"] == email) & (df["activo"] == True)]
    if fila.empty:
        return None
    usuario = fila.iloc[0]
    if usuario["password_hash"] != _hash(password):
        return None
    return _serie_a_dict(usuario)
