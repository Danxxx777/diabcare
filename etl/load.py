"""Carga Parquet a MinIO (paso L del ELT — landing crudo o stage limpio)."""
from __future__ import annotations

import io
import os
import tempfile
from datetime import datetime, timezone

import pandas as pd

PREFIJO_PIPELINE = "pocketbase_elt_"
PREFIJO_RAW = "pocketbase_elt_raw_"


def cargar_parquet_minio(
    df: pd.DataFrame,
    *,
    cliente,
    bucket: str,
    stage_path: str,
    prefijo: str = PREFIJO_PIPELINE,
    etiqueta: str = "Delta cargado",
) -> tuple[str, str]:
    """
    Serializa a Parquet y sube a MinIO.
    ELT: el paso L usa landing/ (crudo); el paso T escribe luego en stage/ (limpio).
    No borra archivos previos (incremental).
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    nombre = f"{prefijo}{ts}.parquet"
    ruta = f"{stage_path}{nombre}"

    tmp_path = None
    data = b""
    try:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name
        df.to_parquet(tmp_path, index=False, engine="pyarrow")
        if not cliente.bucket_exists(bucket):
            cliente.make_bucket(bucket)
        with open(tmp_path, "rb") as f:
            data = f.read()
        cliente.put_object(
            bucket, ruta, io.BytesIO(data), length=len(data),
            content_type="application/octet-stream",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    mb = round(len(data) / 1024 / 1024, 2)
    return nombre, f"{etiqueta} ({mb} MB) — {ruta}"
