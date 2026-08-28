import uuid
import pandas as pd
from datetime import datetime
from nucleo.utilidades.ParquetCache import leer, escribir

BUCKET_APP = "diabcare-app"
ARCHIVO = "usuarios/usuarios.parquet"
COLUMNAS = [
    "id", "nombre", "email", "password_hash", "rol", "activo",
    "creado_en", "debe_cambiar_password",
    "telefono", "cargo", "bio", "idioma", "notif_email",
]

CAMPOS_PERFIL = ("nombre", "telefono", "cargo", "bio", "idioma", "notif_email")
_BOOL_COLS = ("activo", "debe_cambiar_password", "notif_email")

ADMIN_ID = "admin-001"
ADMIN_EMAIL = "admin@diabcare.com"
ADMIN_PASSWORD_DEFAULT = "Admin2026*"


def _coerce_bool(v) -> bool:
    if v is True:
        return True
    if v is False or v is None:
        return False
    if isinstance(v, (int, float)) and not (isinstance(v, float) and pd.isna(v)):
        return bool(v) and v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "si", "sí")
    try:
        if isinstance(v, float) and pd.isna(v):
            return False
    except Exception:
        pass
    return False


def _valor_escritura(col: str, v):
    """Normaliza valores para columnas Arrow (bools → 'true'/'false')."""
    if col in _BOOL_COLS:
        return "true" if _coerce_bool(v) else "false"
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def _normalizar_bools_df(df: pd.DataFrame) -> pd.DataFrame:
    """Evita TypeError al asignar bool en columnas string de Parquet/Arrow."""
    out = df.copy()
    for col in _BOOL_COLS:
        if col not in out.columns:
            continue
        vals = [_valor_escritura(col, x) for x in out[col].tolist()]
        out[col] = pd.Series(vals, index=out.index, dtype=object)
    return out


def asegurar_admin(password: str | None = None, datos: dict | None = None) -> dict:
    """Garantiza que el admin exista en MinIO (para que perfil/foto persistan)."""
    df = _normalizar_bools_df(_extraer())
    email = ADMIN_EMAIL
    idx = []
    if not df.empty:
        idx = df.index[df["id"].astype(str) == ADMIN_ID].tolist()
        if not idx:
            idx = df.index[df["email"].astype(str).str.lower() == email].tolist()

    pwd = password or ADMIN_PASSWORD_DEFAULT
    extras = datos or {}
    if idx:
        i = idx[0]
        df.at[i, "id"] = ADMIN_ID
        df.at[i, "email"] = email
        df.at[i, "rol"] = "administrador"
        df.at[i, "activo"] = _valor_escritura("activo", True)
        if password:
            df.at[i, "password_hash"] = _hash(pwd)
        for k in CAMPOS_PERFIL:
            if k in extras and extras[k] is not None:
                df.at[i, k] = _valor_escritura(k, extras[k])
        _cargar(df)
        return obtener_usuario(ADMIN_ID)

    nuevo = {
        "id": ADMIN_ID,
        "nombre": str(extras.get("nombre") or "Administrador"),
        "email": email,
        "password_hash": _hash(pwd),
        "rol": "administrador",
        "activo": "true",
        "creado_en": datetime.utcnow().isoformat(),
        "debe_cambiar_password": "false",
        "telefono": str(extras.get("telefono") or ""),
        "cargo": str(extras.get("cargo") or ""),
        "bio": str(extras.get("bio") or ""),
        "idioma": str(extras.get("idioma") or "es"),
        "notif_email": _valor_escritura("notif_email", extras.get("notif_email", True)),
    }
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return obtener_usuario(ADMIN_ID)


def _hash(p):
    """Hash bcrypt (no reversible). Reemplaza el SHA-256 anterior."""
    from nucleo.utilidades.PasswordHash import hash_password
    return hash_password(p)


def _asegurar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    for col in COLUMNAS:
        if col not in df.columns:
            if col == "debe_cambiar_password":
                df[col] = "false"
            elif col == "activo":
                df[col] = "true"
            elif col == "notif_email":
                df[col] = "true"
            elif col == "idioma":
                df[col] = "es"
            else:
                df[col] = ""
    return _normalizar_bools_df(df)


def _extraer() -> pd.DataFrame:
    return _asegurar_columnas(leer(BUCKET_APP, ARCHIVO, COLUMNAS))


def _cargar(df: pd.DataFrame):
    df = _normalizar_bools_df(_asegurar_columnas(df))
    escribir(BUCKET_APP, ARCHIVO, df[COLUMNAS])


def _serie_a_dict(serie) -> dict:
    d = serie.to_dict()
    out = {}
    for k, v in d.items():
        if isinstance(v, float) and pd.isna(v):
            out[k] = None
        elif k in _BOOL_COLS:
            out[k] = _coerce_bool(v)
        else:
            out[k] = v
    return out


def _flag_debe_cambiar(val) -> bool:
    return _coerce_bool(val)


def crear_usuario(nombre, email, password, rol, debe_cambiar_password: bool = False):
    df = _extraer()
    email = str(email).strip().lower()
    if not df.empty and email in df["email"].values:
        return {"error": "Email ya registrado"}
    nuevo = {
        "id": str(uuid.uuid4()),
        "nombre": str(nombre),
        "email": email,
        "password_hash": _hash(password),
        "rol": str(rol),
        "activo": "true",
        "creado_en": datetime.utcnow().isoformat(),
        "debe_cambiar_password": _valor_escritura("debe_cambiar_password", debe_cambiar_password),
        "telefono": "",
        "cargo": "",
        "bio": "",
        "idioma": "es",
        "notif_email": "true",
    }
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return {"mensaje": "Usuario creado", "id": nuevo["id"]}


def crear_usuario_con_hash(nombre, email, password_hash, rol, debe_cambiar_password: bool = False):
    email = str(email).strip().lower()
    df = _extraer()
    if not df.empty and email in df["email"].values:
        return {"error": "Email ya registrado"}
    nuevo = {
        "id": str(uuid.uuid4()),
        "nombre": str(nombre),
        "email": email,
        "password_hash": str(password_hash),
        "rol": str(rol),
        "activo": "true",
        "creado_en": datetime.utcnow().isoformat(),
        "debe_cambiar_password": _valor_escritura("debe_cambiar_password", debe_cambiar_password),
        "telefono": "",
        "cargo": "",
        "bio": "",
        "idioma": "es",
        "notif_email": "true",
    }
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return {"mensaje": "Usuario creado", "id": nuevo["id"]}


def obtener_usuarios():
    df = _extraer()
    if df.empty:
        return []
    cols = ["id", "nombre", "email", "rol", "activo", "creado_en", "debe_cambiar_password"]
    return df[cols].fillna("").to_dict(orient="records")


def listar_activos_por_rol(rol: str) -> list:
    df = _extraer()
    if df.empty:
        return []
    sub = df[df["rol"].astype(str).str.lower() == str(rol).lower()]
    if "activo" in sub.columns:
        # astype(bool) es obligatorio: si sub ya viene vacio, .map() devuelve una
        # Series vacia de dtype object y pandas la trata como lista de columnas,
        # no como mascara -> el DataFrame queda sin columnas y el sort revienta.
        sub = sub[sub["activo"].map(_coerce_bool).astype(bool)]
    if sub.empty:
        return []
    sub = sub.sort_values("nombre", kind="stable")
    return sub[["id", "nombre", "email", "rol"]].fillna("").to_dict(orient="records")


def obtener_usuario(id_usuario):
    df = _extraer()
    fila = df[df["id"] == id_usuario]
    if fila.empty:
        return {"error": "Usuario no encontrado"}
    cols = [
        "id", "nombre", "email", "rol", "activo", "debe_cambiar_password",
        "telefono", "cargo", "bio", "idioma", "notif_email", "creado_en",
    ]
    cols = [c for c in cols if c in fila.columns]
    d = fila[cols].fillna("").iloc[0].to_dict()
    d["activo"] = _coerce_bool(d.get("activo", True))
    d["debe_cambiar_password"] = _flag_debe_cambiar(d.get("debe_cambiar_password"))
    d["notif_email"] = _coerce_bool(d.get("notif_email", True))
    d["idioma"] = (str(d.get("idioma") or "es").strip() or "es")
    try:
        from paquetes.clinico.pacientes.FotosEntidadServicio import obtener_principal
        d["tiene_foto"] = bool(obtener_principal("usuario", str(d["id"])))
    except Exception:
        d["tiene_foto"] = False
    return d


def actualizar_perfil_campos(id_usuario: str, datos: dict) -> dict:
    limpio = {}
    if "nombre" in datos and datos["nombre"] is not None:
        nombre = str(datos["nombre"]).strip()
        if len(nombre) < 2:
            return {"error": "El nombre debe tener al menos 2 caracteres"}
        limpio["nombre"] = nombre
    if "telefono" in datos and datos["telefono"] is not None:
        limpio["telefono"] = str(datos["telefono"]).strip()[:40]
    if "cargo" in datos and datos["cargo"] is not None:
        limpio["cargo"] = str(datos["cargo"]).strip()[:80]
    if "bio" in datos and datos["bio"] is not None:
        limpio["bio"] = str(datos["bio"]).strip()[:500]
    if "idioma" in datos and datos["idioma"] is not None:
        idi = str(datos["idioma"]).strip().lower()[:5]
        limpio["idioma"] = idi if idi in ("es", "en") else "es"
    if "notif_email" in datos and datos["notif_email"] is not None:
        limpio["notif_email"] = bool(datos["notif_email"])
    if not limpio:
        return {"error": "Sin cambios"}
    r = editar_usuario(id_usuario, limpio)
    if "error" in r:
        return r
    return {"mensaje": "Perfil actualizado", "usuario": obtener_usuario(id_usuario)}


def obtener_usuario_por_email(email: str):
    df = _extraer()
    if df.empty:
        return {"error": "Usuario no encontrado"}
    fila = df[df["email"].astype(str).str.lower() == str(email).strip().lower()]
    if fila.empty:
        return {"error": "Usuario no encontrado"}
    return obtener_usuario(str(fila.iloc[0]["id"]))


def editar_usuario(id_usuario, cambios):
    df = _extraer()
    idx = df.index[df["id"] == id_usuario].tolist()
    if not idx:
        return {"error": "Usuario no encontrado"}
    for k, v in cambios.items():
        if k == "password_hash":
            continue
        df.at[idx[0], k] = _valor_escritura(k, v)
    _cargar(df)
    return {"mensaje": "Usuario actualizado"}


def desactivar_usuario(id_usuario):
    df = _extraer()
    idx = df.index[df["id"] == id_usuario].tolist()
    if not idx:
        return {"error": "Usuario no encontrado"}
    df.at[idx[0], "activo"] = _valor_escritura("activo", False)
    _cargar(df)
    return {"mensaje": "Usuario desactivado"}


def restablecer_password_temporal_por_email(email: str, password: str) -> dict:
    """Regenera una clave temporal sin exponerla en la respuesta."""
    df = _extraer()
    idx = df.index[df["email"].astype(str).str.lower() == str(email).strip().lower()].tolist()
    if not idx:
        return {"error": "Usuario no encontrado"}
    i = idx[0]
    df.at[i, "password_hash"] = _hash(password)
    df.at[i, "activo"] = _valor_escritura("activo", True)
    df.at[i, "debe_cambiar_password"] = _valor_escritura("debe_cambiar_password", True)
    _cargar(df)
    return {"mensaje": "Contraseña temporal regenerada", "id": str(df.at[i, "id"])}


def asignar_rol(id_usuario, rol):
    df = _extraer()
    idx = df.index[df["id"] == id_usuario].tolist()
    if not idx:
        return {"error": "Usuario no encontrado"}
    df.at[idx[0], "rol"] = str(rol)
    _cargar(df)
    return {"mensaje": f"Rol {rol} asignado"}


def verificar_credenciales(email, password):
    from nucleo.utilidades.PasswordHash import verificar_password, necesita_rehash, hash_password

    df = _extraer()
    if df.empty:
        return None
    mask = (df["email"].astype(str).str.lower() == str(email).strip().lower()) & df["activo"].map(_coerce_bool)
    fila = df[mask]
    if fila.empty:
        return None
    usuario = fila.iloc[0]
    stored = str(usuario.get("password_hash") or "")
    if not verificar_password(password, stored):
        return None
    # Migración silenciosa SHA-256 → bcrypt en el primer login correcto
    if necesita_rehash(stored):
        try:
            i = fila.index[0]
            df.at[i, "password_hash"] = hash_password(password)
            _cargar(df)
            usuario = df.loc[i]
        except Exception:
            pass
    return _serie_a_dict(usuario)
