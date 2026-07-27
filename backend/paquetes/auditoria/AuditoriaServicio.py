"""
AuditoriaServicio — P11 Auditoría y trazabilidad.
"""

import uuid
from datetime import datetime

import pandas as pd

from nucleo.utilidades.ParquetCache import leer, escribir
from nucleo.utilidades.LogConfig import log_advertencia

BUCKET_APP = "diabcare-app"
ARCHIVO = "auditoria/eventos.parquet"
COLUMNAS = [
    "id", "fecha", "usuario", "tipo", "modulo", "detalle",
    "ip", "user_agent", "sesion_id", "resultado",
]


def _extraer() -> pd.DataFrame:
    return leer(BUCKET_APP, ARCHIVO, COLUMNAS)


def _cargar(df: pd.DataFrame):
    for col in COLUMNAS:
        if col not in df.columns:
            df[col] = ""
    escribir(BUCKET_APP, ARCHIVO, df[COLUMNAS])


def registrar(
    usuario: str,
    tipo: str,
    modulo: str,
    detalle: str = "",
    *,
    ip: str = "",
    user_agent: str = "",
    sesion_id: str = "",
    resultado: str = "ok",
) -> None:
    try:
        df = _extraer()
        evento = {
            "id": str(uuid.uuid4()),
            "fecha": datetime.now().isoformat(),
            "usuario": str(usuario or "desconocido"),
            "tipo": str(tipo or "info"),
            "modulo": str(modulo or "-"),
            "detalle": str(detalle or ""),
            "ip": str(ip or "")[:80],
            "user_agent": str(user_agent or "")[:200],
            "sesion_id": str(sesion_id or "")[:64],
            "resultado": str(resultado or "ok"),
        }
        _cargar(pd.concat([df, pd.DataFrame([evento])], ignore_index=True))
    except Exception as e:
        log_advertencia(f"Auditoría: no se pudo registrar evento: {e}")


def listar(
    skip: int = 0,
    limit: int = 50,
    tipo: str = None,
    usuario: str = None,
    modulo: str = None,
    resultado: str = None,
) -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "eventos": []}
    if tipo:
        df = df[df["tipo"].astype(str) == tipo]
    if usuario:
        df = df[df["usuario"].astype(str).str.contains(usuario, case=False, na=False)]
    if modulo:
        df = df[df["modulo"].astype(str) == modulo]
    if resultado:
        df = df[df["resultado"].astype(str) == resultado]
    df = df.sort_values("fecha", ascending=False)
    total = int(len(df))
    pagina = df.iloc[skip:skip + limit]
    return {"total": total, "eventos": pagina.fillna("").to_dict(orient="records")}


def estadisticas() -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "hoy": 0, "errores": 0, "usuarios": 0, "fallos": 0}
    hoy = datetime.now().strftime("%Y-%m-%d")
    return {
        "total": int(len(df)),
        "hoy": int(df["fecha"].astype(str).str.startswith(hoy).sum()),
        "errores": int((df["tipo"] == "error").sum()),
        "fallos": int((df.get("resultado", pd.Series(dtype=str)).astype(str) == "fallo").sum())
        if "resultado" in df.columns else 0,
        "usuarios": int(df["usuario"].nunique()),
    }
