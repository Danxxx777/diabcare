"""Sesiones JWT activas — registro / revocación en MinIO (con índice en memoria)."""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timedelta

import pandas as pd

from nucleo.utilidades.ParquetCache import leer, escribir, invalidar

BUCKET_APP = "diabcare-app"
ARCHIVO = "usuarios/sesiones.parquet"
COLUMNAS = [
    "id_sesion", "id_usuario", "email", "ip", "user_agent",
    "creado_en", "expira_en", "revocada", "revocada_en",
]
MAX_SESIONES = 5

# Índice en memoria: evita MinIO en CADA request autenticado
_idx_lock = threading.RLock()
_idx_ts = 0.0
_idx_ttl = 20.0
_revocadas: set[str] = set()
_activas_exp: dict[str, float] = {}  # jti -> unix exp


def _es_revocada(val) -> bool:
    if val is True:
        return True
    if val is False or val is None:
        return False
    if isinstance(val, str) and val.strip().lower() in ("true", "1", "yes", "si", "sí"):
        return True
    return False


def _flag_escritura(val) -> str:
    """Arrow string-safe: nunca escribir bool puro en Parquet tipado como str."""
    return "true" if _es_revocada(val) else "false"


def _extraer() -> pd.DataFrame:
    df = leer(BUCKET_APP, ARCHIVO, COLUMNAS, ttl=_idx_ttl)
    if df.empty:
        return df
    out = df.copy()
    if "revocada" in out.columns:
        out["revocada"] = pd.Series(
            [_flag_escritura(x) for x in out["revocada"].tolist()],
            index=out.index,
            dtype=object,
        )
    return out


def _cargar(df: pd.DataFrame) -> None:
    for col in COLUMNAS:
        if col not in df.columns:
            df[col] = "false" if col == "revocada" else ""
    if "revocada" in df.columns:
        df = df.copy()
        df["revocada"] = [_flag_escritura(x) for x in df["revocada"].tolist()]
    escribir(BUCKET_APP, ARCHIVO, df[COLUMNAS])
    _reconstruir_indice(df)


def _reconstruir_indice(df: pd.DataFrame | None = None) -> None:
    global _idx_ts, _revocadas, _activas_exp
    if df is None:
        df = _extraer()
    rev: set[str] = set()
    act: dict[str, float] = {}
    if not df.empty:
        for _, row in df.iterrows():
            jti = str(row.get("id_sesion") or "")
            if not jti:
                continue
            if _es_revocada(row.get("revocada")):
                rev.add(jti)
                continue
            try:
                exp = datetime.fromisoformat(str(row.get("expira_en", ""))).timestamp()
            except Exception:
                exp = time.time() + 3600
            if exp < time.time():
                rev.add(jti)
            else:
                act[jti] = exp
    with _idx_lock:
        _revocadas = rev
        _activas_exp = act
        _idx_ts = time.monotonic()


def _asegurar_indice() -> None:
    with _idx_lock:
        fresco = (time.monotonic() - _idx_ts) < _idx_ttl and _idx_ts > 0
        if fresco:
            return
    _reconstruir_indice()


def crear_sesion(
    id_usuario: str,
    email: str,
    horas: int = 8,
    ip: str = "",
    user_agent: str = "",
) -> str:
    df = _extraer()
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    exp_dt = now + timedelta(hours=horas)
    fila = {
        "id_sesion": jti,
        "id_usuario": str(id_usuario),
        "email": str(email),
        "ip": str(ip or "")[:120],
        "user_agent": str(user_agent or "")[:250],
        "creado_en": now.isoformat(),
        "expira_en": exp_dt.isoformat(),
        "revocada": "false",
        "revocada_en": "",
    }
    df = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)

    activas = df[
        (df["id_usuario"].astype(str) == str(id_usuario))
        & (~df["revocada"].map(_es_revocada))
    ].sort_values("creado_en", ascending=True)
    if len(activas) > MAX_SESIONES:
        exceso = activas.iloc[: len(activas) - MAX_SESIONES]
        for sid in exceso["id_sesion"].tolist():
            idx = df.index[df["id_sesion"].astype(str) == str(sid)].tolist()
            if idx:
                df.at[idx[0], "revocada"] = _flag_escritura(True)
                df.at[idx[0], "revocada_en"] = now.isoformat()

    _cargar(df)
    with _idx_lock:
        _activas_exp[jti] = exp_dt.timestamp()
        _revocadas.discard(jti)
    return jti


def sesion_valida(jti: str) -> bool:
    """Hot path: solo memoria; refresca índice a lo sumo cada TTL."""
    if not jti:
        return True
    _asegurar_indice()
    with _idx_lock:
        if jti in _revocadas:
            return False
        exp = _activas_exp.get(jti)
        if exp is None:
            return False
        if exp < time.time():
            _revocadas.add(jti)
            _activas_exp.pop(jti, None)
            return False
        return True


def revocar(jti: str) -> dict:
    if not jti:
        return {"error": "Sesión no indicada"}
    df = _extraer()
    idx = df.index[df["id_sesion"].astype(str) == str(jti)].tolist()
    if not idx:
        with _idx_lock:
            _revocadas.add(str(jti))
            _activas_exp.pop(str(jti), None)
        return {"error": "Sesión no encontrada"}
    df.at[idx[0], "revocada"] = _flag_escritura(True)
    df.at[idx[0], "revocada_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    with _idx_lock:
        _revocadas.add(str(jti))
        _activas_exp.pop(str(jti), None)
    return {"mensaje": "Sesión revocada"}


def revocar_todas_usuario(id_usuario: str, excepto: str | None = None, email: str | None = None) -> int:
    df = _extraer()
    if df.empty:
        return 0
    n = 0
    now = datetime.utcnow().isoformat()
    email_l = (email or "").strip().lower()
    for i, row in df.iterrows():
        mismo_id = str(row.get("id_usuario")) == str(id_usuario)
        mismo_mail = bool(email_l) and str(row.get("email") or "").strip().lower() == email_l
        if not (mismo_id or mismo_mail):
            continue
        if excepto and str(row.get("id_sesion")) == str(excepto):
            continue
        if _es_revocada(row.get("revocada")):
            continue
        df.at[i, "revocada"] = _flag_escritura(True)
        df.at[i, "revocada_en"] = now
        n += 1
        with _idx_lock:
            sid = str(row.get("id_sesion"))
            _revocadas.add(sid)
            _activas_exp.pop(sid, None)
    if n:
        _cargar(df)
    return n


def _normalizar_fila_sesion(row: dict) -> dict:
    out = dict(row)
    out["revocada"] = _es_revocada(out.get("revocada"))
    return out


def listar_usuario(id_usuario: str, email: str | None = None) -> list:
    """Lista sesiones del usuario por id y, si se indica, también por email (migración admin)."""
    df = _extraer()
    if df.empty:
        return []
    mask = df["id_usuario"].astype(str) == str(id_usuario)
    if email:
        mask = mask | (df["email"].astype(str).str.lower() == str(email).strip().lower())
    sub = df[mask].copy()
    sub = sub.sort_values("creado_en", ascending=False)
    return [_normalizar_fila_sesion(r) for r in sub.fillna("").to_dict(orient="records")]


def pertenece_a_usuario(id_sesion: str, id_usuario: str, email: str | None = None) -> bool:
    df = _extraer()
    if df.empty:
        return False
    fila = df[df["id_sesion"].astype(str) == str(id_sesion)]
    if fila.empty:
        return False
    row = fila.iloc[0]
    if str(row.get("id_usuario")) == str(id_usuario):
        return True
    if email and str(row.get("email") or "").strip().lower() == str(email).strip().lower():
        return True
    return False


def listar_todas(skip: int = 0, limit: int = 50, solo_activas: bool = True) -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "sesiones": []}
    if solo_activas:
        df = df[~df["revocada"].map(_es_revocada)]
    df = df.sort_values("creado_en", ascending=False)
    total = int(len(df))
    pagina = df.iloc[skip: skip + limit]
    return {
        "total": total,
        "sesiones": [_normalizar_fila_sesion(r) for r in pagina.fillna("").to_dict(orient="records")],
    }


def limpiar_seguridad() -> None:
    invalidar(BUCKET_APP, ARCHIVO)
    with _idx_lock:
        global _idx_ts
        _idx_ts = 0
