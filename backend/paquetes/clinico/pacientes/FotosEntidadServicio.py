"""
Metadatos en Parquet (oper_fotos_entidad) + binarios en MinIO (diabcare-app).
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime

import pandas as pd

from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO_META = "operativo/fotos_entidad.parquet"
PREFIX_BIN = "operativo/fotos/binario/"
COLUMNAS = [
    "id_foto", "tipo_entidad", "id_entidad", "nombre_archivo", "mime_type",
    "ruta_minio", "es_principal", "subido_en", "subido_por",
]
MAX_BYTES = 5 * 1024 * 1024
MIME_OK = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}


def _es_true(val) -> bool:
    if val is True:
        return True
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "si", "sí")
    try:
        return bool(val) and str(val).lower() not in ("false", "0", "no", "none", "nan")
    except Exception:
        return False


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


def _ext(mime: str) -> str:
    m = (mime or "").lower()
    if "png" in m:
        return ".png"
    if "webp" in m:
        return ".webp"
    if "gif" in m:
        return ".gif"
    return ".jpg"


def guardar_foto(
    tipo_entidad: str,
    id_entidad: str,
    contenido: bytes,
    mime_type: str,
    usuario: str = "sistema",
    es_principal: bool = True,
) -> dict:
    if not contenido:
        return {"error": "Archivo vacío"}
    if len(contenido) > MAX_BYTES:
        return {"error": "La imagen no puede superar 5 MB"}
    mime = (mime_type or "image/jpeg").split(";")[0].strip().lower()
    if mime not in MIME_OK:
        return {"error": "Formato no permitido (use JPEG, PNG o WebP)"}

    id_foto = str(uuid.uuid4())
    ext = _ext(mime)
    nombre = f"foto{ext}"
    ruta = f"{PREFIX_BIN}{tipo_entidad}/{id_entidad}/{id_foto}{ext}"

    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    c.put_object(
        BUCKET_APP, ruta, io.BytesIO(contenido), len(contenido), content_type=mime,
    )

    df = _extraer()
    if es_principal and not df.empty:
        mask = (
            (df["tipo_entidad"] == tipo_entidad)
            & (df["id_entidad"].astype(str) == str(id_entidad))
            & (df["es_principal"].map(_es_true))
        )
        df.loc[mask, "es_principal"] = False

    fila = {
        "id_foto": id_foto,
        "tipo_entidad": tipo_entidad,
        "id_entidad": str(id_entidad),
        "nombre_archivo": nombre,
        "mime_type": mime,
        "ruta_minio": ruta,
        "es_principal": es_principal,
        "subido_en": datetime.utcnow().isoformat(),
        "subido_por": str(usuario or "sistema"),
    }
    _cargar(pd.concat([df, pd.DataFrame([fila])], ignore_index=True))
    return {"mensaje": "Foto guardada", "id_foto": id_foto, "ruta_minio": ruta}


def obtener_principal(tipo_entidad: str, id_entidad: str) -> dict | None:
    df = _extraer()
    if df.empty:
        return None
    sub = df[
        (df["tipo_entidad"] == tipo_entidad)
        & (df["id_entidad"].astype(str) == str(id_entidad))
    ]
    if sub.empty:
        return None
    prin = sub[sub["es_principal"].map(_es_true)]
    row = prin.iloc[0] if not prin.empty else sub.sort_values("subido_en", ascending=False).iloc[0]
    return row.fillna("").to_dict()


def leer_bytes_foto(tipo_entidad: str, id_entidad: str) -> dict:
    meta = obtener_principal(tipo_entidad, id_entidad)
    if not meta:
        return {"error": "Sin foto"}
    try:
        c = get_cliente()
        obj = c.get_object(BUCKET_APP, meta["ruta_minio"])
        data = obj.read()
        return {
            "contenido": data,
            "mime_type": meta.get("mime_type") or "image/jpeg",
            "id_foto": meta.get("id_foto"),
        }
    except Exception as e:
        return {"error": f"No se pudo leer la foto: {e}"}
