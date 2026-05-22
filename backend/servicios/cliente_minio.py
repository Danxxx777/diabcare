"""
cliente_minio.py — Servicio de conexión a MinIO y carga del DataFrame
"""

from minio import Minio
from io import BytesIO
from fastapi import HTTPException
import pandas as pd

# ── Configuración MinIO ────────────────────────────────────────────────────────
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS   = "admin"
MINIO_SECRET   = "password123"
MINIO_BUCKET   = "diabetes-data"
MINIO_PREFIX   = "stage/"

# ── Caché del DataFrame ────────────────────────────────────────────────────────
_df_cache: pd.DataFrame = None


def get_cliente_minio() -> Minio:
    """Retorna una instancia del cliente MinIO."""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS,
        secret_key=MINIO_SECRET,
        secure=False
    )

def get_df() -> pd.DataFrame:
    """Carga y combina todos los parquets de MinIO stage/ y los cachea en memoria."""
    global _df_cache
    if _df_cache is not None:
        return _df_cache
    cliente = get_cliente_minio()
    objetos = list(cliente.list_objects(MINIO_BUCKET, prefix=MINIO_PREFIX))
    if not objetos:
        raise HTTPException(status_code=404, detail="No hay archivos parquet en MinIO stage/")
    archivos_parquet = [o for o in objetos if o.object_name.endswith(".parquet")]
    if not archivos_parquet:
        raise HTTPException(status_code=404, detail="No se encontraron archivos .parquet")
    dfs = []
    for archivo in archivos_parquet:
        print(f"Cargando: {archivo.object_name}")
        respuesta = cliente.get_object(MINIO_BUCKET, archivo.object_name)
        datos = BytesIO(respuesta.read())
        dfs.append(pd.read_parquet(datos))
    _df_cache = pd.concat(dfs, ignore_index=True)
    print(f"Dataset combinado: {len(_df_cache)} registros")
    return _df_cache

    
def limpiar_cache():
    """Limpia la caché para forzar recarga desde MinIO."""
    global _df_cache
    _df_cache = None
