# -*- coding: utf-8 -*-
"""Caché en memoria de Parquet en MinIO (TTL + invalidación en escritura).

Evita descargar el mismo objeto en cada request (auth, listados, KPIs).
"""
from __future__ import annotations

import io
import threading
import time
from typing import Optional

import pandas as pd

from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

_lock = threading.RLock()
_frames: dict[str, tuple[float, pd.DataFrame]] = {}
_buckets_ok: set[str] = set()

# TTL corto: datos frescos sin martillar MinIO en cada click
TTL_DEFAULT = 12.0


def _key(bucket: str, archivo: str) -> str:
    return f"{bucket}::{archivo}"


def asegurar_bucket(bucket: str) -> None:
    with _lock:
        if bucket in _buckets_ok:
            return
        c = get_cliente()
        if not c.bucket_exists(bucket):
            c.make_bucket(bucket)
        _buckets_ok.add(bucket)


def leer(
    bucket: str,
    archivo: str,
    columnas: Optional[list[str]] = None,
    *,
    ttl: float = TTL_DEFAULT,
) -> pd.DataFrame:
    """Lee Parquet con caché TTL. Devuelve copia para no mutar el cache."""
    k = _key(bucket, archivo)
    now = time.monotonic()
    with _lock:
        hit = _frames.get(k)
        if hit is not None and (now - hit[0]) < ttl:
            return hit[1].copy()

    try:
        asegurar_bucket(bucket)
        c = get_cliente()
        obj = c.get_object(bucket, archivo)
        raw = obj.read()
        try:
            obj.close()
            obj.release_conn()
        except Exception:
            pass
        df = pd.read_parquet(io.BytesIO(raw))
        if columnas:
            for col in columnas:
                if col not in df.columns:
                    df[col] = True if col == "activo" else False if col in ("leida", "email_enviado", "revocada", "debe_cambiar_password") else ""
    except Exception:
        df = pd.DataFrame(columns=list(columnas or []))

    with _lock:
        _frames[k] = (time.monotonic(), df)
        return df.copy()


def escribir(bucket: str, archivo: str, df: pd.DataFrame) -> None:
    asegurar_bucket(bucket)
    c = get_cliente()
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(bucket, archivo, buf, buf.getbuffer().nbytes)
    invalidar(bucket, archivo)
    # Deja el DF fresco en caché (evita re-descarga inmediata post-escritura)
    with _lock:
        _frames[_key(bucket, archivo)] = (time.monotonic(), df.copy())


def invalidar(bucket: str | None = None, archivo: str | None = None) -> None:
    with _lock:
        if bucket is None and archivo is None:
            _frames.clear()
            return
        if archivo is None:
            prefix = f"{bucket}::"
            for k in list(_frames):
                if k.startswith(prefix):
                    _frames.pop(k, None)
            return
        _frames.pop(_key(bucket or "diabcare-app", archivo), None)


def get_cache_stats() -> dict:
    with _lock:
        return {"entradas": len(_frames), "buckets": list(_buckets_ok)}
