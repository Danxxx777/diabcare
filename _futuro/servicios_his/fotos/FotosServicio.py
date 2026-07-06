"""Metadatos y almacenamiento de fotos de personas en MinIO."""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

import pandas as pd

from servicios.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO_META = "operativo/fotos_entidad.parquet"
PREFIX_BIN = "fotos/"
MAX_BYTES = 5 * 1024 * 1024
MIME_PERMITIDOS = {"image/jpeg", "image/png", "image/webp", "image/gif"}
TIPOS_ENTIDAD = frozenset({"paciente", "usuario", "medico", "contacto"})

COLUMNAS = [
    "id_foto", "tipo_entidad", "id_entidad", "nombre_archivo", "mime_type",
    "ruta_minio", "es_principal", "subido_en", "subido_por",
]


def _extraer() -> pd.DataFrame:
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        obj = c.get_object(BUCKET_APP, ARCHIVO_META)
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
    c.put_object(BUCKET_APP, ARCHIVO_META, buf, buf.getbuffer().nbytes)


def _ext_desde_mime(mime: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(mime, ".bin")


def listar(tipo_entidad: str, id_entidad: str) -> dict:
    tipo = str(tipo_entidad).strip().lower()
    if tipo not in TIPOS_ENTIDAD:
        return {"error": f"tipo_entidad inválido. Use: {', '.join(sorted(TIPOS_ENTIDAD))}"}
    df = _extraer()
    if df.empty:
        return {"fotos": [], "total": 0}
    mask = (df["tipo_entidad"] == tipo) & (df["id_entidad"].astype(str) == str(id_entidad))
    rows = df[mask].sort_values("es_principal", ascending=False).fillna("").to_dict(orient="records")
    return {"fotos": rows, "total": len(rows)}


def obtener_principal(tipo_entidad: str, id_entidad: str) -> dict | None:
    res = listar(tipo_entidad, id_entidad)
    fotos = res.get("fotos") or []
    if not fotos:
        return None
    for f in fotos:
        if f.get("es_principal"):
            return f
    return fotos[0]


def subir(
    tipo_entidad: str,
    id_entidad: str,
    contenido: bytes,
    mime_type: str,
    nombre_archivo: str,
    subido_por: str,
    es_principal: bool = True,
) -> dict:
    tipo = str(tipo_entidad).strip().lower()
    if tipo not in TIPOS_ENTIDAD:
        return {"error": f"tipo_entidad inválido. Use: {', '.join(sorted(TIPOS_ENTIDAD))}"}
    if not id_entidad or not str(id_entidad).strip():
        return {"error": "id_entidad requerido"}
    if len(contenido) > MAX_BYTES:
        return {"error": f"Archivo demasiado grande (máx. {MAX_BYTES // (1024*1024)} MB)"}
    mime = (mime_type or "").split(";")[0].strip().lower()
    if mime not in MIME_PERMITIDOS:
        return {"error": "Formato no permitido. Use JPEG, PNG, WebP o GIF."}

    id_foto = str(uuid.uuid4())
    ext = _ext_desde_mime(mime)
    ruta = f"{PREFIX_BIN}{tipo}/{id_entidad}/{id_foto}{ext}"
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    c.put_object(BUCKET_APP, ruta, io.BytesIO(contenido), len(contenido), content_type=mime)

    ahora = datetime.now(timezone.utc).isoformat()
    df = _extraer()
    if es_principal and not df.empty:
        mask = (df["tipo_entidad"] == tipo) & (df["id_entidad"].astype(str) == str(id_entidad))
        df.loc[mask, "es_principal"] = False

    fila = {
        "id_foto": id_foto,
        "tipo_entidad": tipo,
        "id_entidad": str(id_entidad),
        "nombre_archivo": nombre_archivo or f"foto{ext}",
        "mime_type": mime,
        "ruta_minio": ruta,
        "es_principal": bool(es_principal),
        "subido_en": ahora,
        "subido_por": subido_por,
    }
    _cargar(pd.concat([df, pd.DataFrame([fila])], ignore_index=True))
    return {"mensaje": "Foto guardada", "foto": fila}


def leer_binario(id_foto: str) -> tuple[bytes, str] | None:
    df = _extraer()
    fila = df[df["id_foto"] == id_foto]
    if fila.empty:
        return None
    ruta = str(fila.iloc[0]["ruta_minio"])
    mime = str(fila.iloc[0]["mime_type"])
    try:
        c = get_cliente()
        obj = c.get_object(BUCKET_APP, ruta)
        return obj.read(), mime
    except Exception:
        return None


def eliminar(id_foto: str) -> dict:
    df = _extraer()
    idx = df.index[df["id_foto"] == id_foto].tolist()
    if not idx:
        return {"error": "Foto no encontrada"}
    ruta = str(df.at[idx[0], "ruta_minio"])
    try:
        c = get_cliente()
        c.remove_object(BUCKET_APP, ruta)
    except Exception:
        pass
    df = df.drop(idx).reset_index(drop=True)
    _cargar(df)
    return {"mensaje": "Foto eliminada", "id_foto": id_foto}
