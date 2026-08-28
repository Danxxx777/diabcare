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

# TTL: reutiliza lecturas entre pantallas sin martillar MinIO en cada click.
# Escrituras invalidan/actualizan la entrada vía escribir().
TTL_DEFAULT = 180.0
# HIS operativo (pacientes/citas/admisiones) cabe en RAM; el workpanel enorme no pasa de MAX_BYTES.
MAX_ENTRADAS = 24
MAX_BYTES = 96 * 1024 * 1024


def _key(bucket: str, archivo: str) -> str:
    return f"{bucket}::{archivo}"


def _tamano(df: pd.DataFrame) -> int:
    try:
        return int(df.memory_usage(index=True, deep=False).sum())
    except Exception:
        return 0


def _guardar(k: str, df: pd.DataFrame) -> None:
    """Guarda en caché si cabe; expulsa la entrada más vieja si hay demasiadas."""
    if _tamano(df) > MAX_BYTES:
        _frames.pop(k, None)
        return
    _frames[k] = (time.monotonic(), df)
    extra = len(_frames) - MAX_ENTRADAS
    if extra <= 0:
        return
    viejas = sorted(((kk, vv[0]) for kk, vv in _frames.items() if kk != k), key=lambda x: x[1])
    for kk, _ in viejas[:extra]:
        _frames.pop(kk, None)


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
    copiar: bool = True,
) -> pd.DataFrame:
    """Lee Parquet con caché TTL.

    Por defecto devuelve copia (seguro para mutar). Usa copiar=False solo
    en lecturas de solo-agregación que no modifican el DataFrame.
    """
    k = _key(bucket, archivo)
    now = time.monotonic()
    with _lock:
        hit = _frames.get(k)
        if hit is not None and (now - hit[0]) < ttl:
            return hit[1].copy() if copiar else hit[1]

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
        # No cachear vacio: un fallo de MinIO no debe "borrar" sesiones/usuarios en memoria.
        with _lock:
            hit = _frames.get(k)
            if hit is not None:
                return hit[1].copy() if copiar else hit[1]
        return pd.DataFrame(columns=list(columnas or []))

    with _lock:
        _guardar(k, df)
        hit = _frames.get(k)
        base = hit[1] if hit is not None else df
        return base.copy() if copiar else base

def escribir(bucket: str, archivo: str, df: pd.DataFrame) -> None:
    asegurar_bucket(bucket)
    c = get_cliente()
    buf = io.BytesIO()
    # engine pyarrow es el default; compression snappy acelera I/O en MinIO
    df.to_parquet(buf, index=False, compression="snappy")
    buf.seek(0)
    c.put_object(bucket, archivo, buf, buf.getbuffer().nbytes)
    k = _key(bucket, archivo)
    with _lock:
        _conteos[k] = (time.monotonic(), int(len(df)))
        if _tamano(df) <= MAX_BYTES:
            _guardar(k, df.copy())
        else:
            _frames.pop(k, None)
    # KPIs del Panel dependen de operativo/negocio: invalidar memo al escribir
    if archivo.startswith(("operativo/", "negocio/")):
        try:
            from paquetes.dataset.DatasetKpisServicio import invalidar_memo_kpis
            invalidar_memo_kpis()
        except Exception:
            pass

def invalidar(bucket: str | None = None, archivo: str | None = None) -> None:
    with _lock:
        if bucket is None and archivo is None:
            _frames.clear()
            _conteos.clear()
            return
        if archivo is None:
            prefix = f"{bucket}::"
            for k in list(_frames):
                if k.startswith(prefix):
                    _frames.pop(k, None)
            for k in list(_conteos):
                if k.startswith(prefix):
                    _conteos.pop(k, None)
            return
        clave = _key(bucket or "diabcare-app", archivo)
        _frames.pop(clave, None)
        _conteos.pop(clave, None)


_conteos: dict[str, tuple[float, int]] = {}
TTL_CONTEO = 60.0


def contar_filas(bucket: str, archivo: str, *, ttl: float = TTL_CONTEO) -> int:
    """Filas de un Parquet sin materializarlo.

    El catalogo del DWH son 69 tablas; contarlas con len(read_parquet(...))
    obligaba a construir DataFrames de millones de filas solo para mostrar un
    numero. Aqui se lee unicamente el footer del Parquet.
    """
    k = _key(bucket, archivo)
    now = time.monotonic()
    with _lock:
        hit = _frames.get(k)
        if hit is not None and (now - hit[0]) < TTL_DEFAULT:
            return int(len(hit[1]))
        cached = _conteos.get(k)
        if cached is not None and (now - cached[0]) < ttl:
            return cached[1]

    try:
        import pyarrow.parquet as pq

        asegurar_bucket(bucket)
        c = get_cliente()
        obj = c.get_object(bucket, archivo)
        raw = obj.read()
        try:
            obj.close()
            obj.release_conn()
        except Exception:
            pass
        total = int(pq.ParquetFile(io.BytesIO(raw)).metadata.num_rows)
    except Exception:
        return 0

    with _lock:
        _conteos[k] = (time.monotonic(), total)
    return total


def get_cache_stats() -> dict:
    with _lock:
        return {"entradas": len(_frames), "buckets": list(_buckets_ok)}
