"""
AuditoriaServicio — P11 Auditoría y trazabilidad (departamento Gobierno y Cumplimiento).

Registra y consulta eventos del sistema (RG-005 de la especificación general y
Principio V de la constitución). Persiste en MinIO `diabcare-app` como Parquet,
siguiendo el mismo patrón que UsuariosServicio.
"""

import io
import uuid
from datetime import datetime

import pandas as pd

from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
from nucleo.utilidades.LogConfig import log_advertencia

BUCKET_APP = "diabcare-app"
ARCHIVO = "auditoria/eventos.parquet"
COLUMNAS = ["id", "fecha", "usuario", "tipo", "modulo", "detalle"]


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


def registrar(usuario: str, tipo: str, modulo: str, detalle: str = "") -> None:
    """
    Registra un evento de auditoría. Resiliente: nunca lanza excepción al llamador
    (una falla de auditoría no debe romper la operación de negocio).
    """
    try:
        df = _extraer()
        evento = {
            "id": str(uuid.uuid4()),
            "fecha": datetime.now().isoformat(),
            "usuario": str(usuario or "desconocido"),
            "tipo": str(tipo or "info"),
            "modulo": str(modulo or "-"),
            "detalle": str(detalle or ""),
        }
        _cargar(pd.concat([df, pd.DataFrame([evento])], ignore_index=True))
    except Exception as e:
        log_advertencia(f"Auditoría: no se pudo registrar evento: {e}")


def listar(skip: int = 0, limit: int = 50, tipo: str = None) -> dict:
    """Lista eventos ordenados del más reciente al más antiguo, con paginación."""
    df = _extraer()
    if df.empty:
        return {"total": 0, "eventos": []}
    if tipo:
        df = df[df["tipo"] == tipo]
    df = df.sort_values("fecha", ascending=False)
    total = int(len(df))
    pagina = df.iloc[skip:skip + limit]
    return {"total": total, "eventos": pagina.fillna("").to_dict(orient="records")}


def estadisticas() -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "hoy": 0, "errores": 0, "usuarios": 0}
    hoy = datetime.now().strftime("%Y-%m-%d")
    return {
        "total": int(len(df)),
        "hoy": int(df["fecha"].astype(str).str.startswith(hoy).sum()),
        "errores": int((df["tipo"] == "error").sum()),
        "usuarios": int(df["usuario"].nunique()),
    }
