"""
NotificacionesServicio — P10 Notificaciones y alertas (departamento Crecimiento e
Integraciones). Gestiona el centro de alertas del sistema. Persiste en MinIO
`diabcare-app/notificaciones/notificaciones.parquet` (mismo patrón que UsuariosServicio).
"""

import io
import uuid
from datetime import datetime

import pandas as pd

from servicios.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "notificaciones/notificaciones.parquet"
COLUMNAS = ["id", "titulo", "mensaje", "tipo", "leida", "creado_en"]
TIPOS_VALIDOS = {"info", "warning", "error", "success"}


def _extraer() -> pd.DataFrame:
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)


def _cargar(df: pd.DataFrame):
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, ARCHIVO, buf, buf.getbuffer().nbytes)


def crear(titulo: str, mensaje: str, tipo: str = "info") -> dict:
    """Crea una notificación. Resiliente: no lanza excepción al llamador."""
    if tipo not in TIPOS_VALIDOS:
        tipo = "info"
    try:
        df = _extraer()
        nueva = {
            "id": str(uuid.uuid4()),
            "titulo": str(titulo),
            "mensaje": str(mensaje),
            "tipo": tipo,
            "leida": False,
            "creado_en": datetime.now().isoformat(),
        }
        _cargar(pd.concat([df, pd.DataFrame([nueva])], ignore_index=True))
        return {"mensaje": "Notificación creada", "id": nueva["id"]}
    except Exception as e:
        print(f"[Notificaciones] No se pudo crear: {e}")
        return {"error": str(e)}


def listar(tipo: str = None) -> list:
    df = _extraer()
    if df.empty:
        return []
    if tipo:
        df = df[df["tipo"] == tipo]
    df = df.sort_values("creado_en", ascending=False)
    return df.fillna("").to_dict(orient="records")


def marcar_todas_leidas() -> dict:
    df = _extraer()
    if df.empty:
        return {"mensaje": "Sin notificaciones", "actualizadas": 0}
    pendientes = int((~df["leida"].astype(bool)).sum())
    df["leida"] = True
    _cargar(df)
    return {"mensaje": "Notificaciones marcadas como leídas", "actualizadas": pendientes}
