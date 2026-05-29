import io
from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Optional
from servicios.dataset.DatasetServicio import generar_y_subir
from servicios.configuracion.ConfiguracionClienteMinio import get_cliente
from servicios.configuracion.ConfiguracionAjustes import MINIO_BUCKET
import pandas as pd

router = APIRouter(prefix='/api/dataset', tags=['Dataset'])

BUCKET_APP = "diabcare-app"

class GenerarEntrada(BaseModel):
    cantidad: int = 100000
    year: int = 2025

# ── HELPERS ──
def _leer_parquet_minio(bucket: str, path: str) -> pd.DataFrame:
    try:
        c = get_cliente()
        obj = c.get_object(bucket, path)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame()

def _leer_ultimo_parquet(prefix: str) -> pd.DataFrame:
    """Lee el parquet más reciente bajo un prefix en el bucket principal."""
    try:
        c = get_cliente()
        objetos = list(c.list_objects(MINIO_BUCKET, prefix=prefix, recursive=True))
        if not objetos:
            return pd.DataFrame()
        ultimo = sorted(objetos, key=lambda o: o.last_modified, reverse=True)[0]
        obj = c.get_object(MINIO_BUCKET, ultimo.object_name)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame()

# ── GENERAR ──
@router.post("/generar")
def generar(datos: GenerarEntrada):
    return generar_y_subir(datos.cantidad, datos.year)

# ── HECHOS ──
@router.get("/hechos")
def listar_hechos(skip: int = 0, limit: int = 50, authorization: Optional[str] = Header(None)):
    df = _leer_ultimo_parquet("stage/")
    if df.empty:
        return {"datos": [], "total": 0, "skip": skip, "limit": limit}
    total = len(df)
    chunk = df.iloc[skip:skip+limit]
    return {
        "datos": chunk.fillna("").to_dict(orient="records"),
        "total": total,
        "skip": skip,
        "limit": limit
    }

# ── DIMENSIONES ──
@router.get("/dimension/paciente")
def dim_paciente(skip: int = 0, limit: int = 50, authorization: Optional[str] = Header(None)):
    df = _leer_parquet_minio(BUCKET_APP, "dimensiones/dim_paciente.parquet")
    if df.empty:
        # Fallback: derivar del dataset principal
        df = _leer_ultimo_parquet("stage/")
        if not df.empty and "age" in df.columns:
            cols = [c for c in ["age", "gender", "bmi", "smoking_history"] if c in df.columns]
            df = df[cols].drop_duplicates().reset_index(drop=True)
            df.insert(0, "id_paciente", range(1, len(df)+1))
    if df.empty:
        return {"datos": [], "total": 0}
    total = len(df)
    chunk = df.iloc[skip:skip+limit]
    return {"datos": chunk.fillna("").to_dict(orient="records"), "total": total}

@router.get("/dimension/ubicacion")
def dim_ubicacion(skip: int = 0, limit: int = 50, authorization: Optional[str] = Header(None)):
    df = _leer_parquet_minio(BUCKET_APP, "dimensiones/dim_ubicacion.parquet")
    if df.empty:
        df = _leer_ultimo_parquet("stage/")
        if not df.empty and "location" in df.columns:
            locs = df["location"].dropna().unique()
            df = pd.DataFrame({"id_ubicacion": range(1, len(locs)+1), "location": locs})
    if df.empty:
        return {"datos": [], "total": 0}
    total = len(df)
    chunk = df.iloc[skip:skip+limit]
    return {"datos": chunk.fillna("").to_dict(orient="records"), "total": total}

@router.get("/dimension/raza")
def dim_raza(skip: int = 0, limit: int = 50, authorization: Optional[str] = Header(None)):
    df = _leer_parquet_minio(BUCKET_APP, "dimensiones/dim_raza.parquet")
    if df.empty:
        razas = ["AfricanAmerican", "Asian", "Caucasian", "Hispanic", "Other"]
        df = pd.DataFrame({"id_raza": range(1, len(razas)+1), "raza": razas})
    total = len(df)
    chunk = df.iloc[skip:skip+limit]
    return {"datos": chunk.fillna("").to_dict(orient="records"), "total": total}

@router.get("/dimension/condicion")
def dim_condicion(skip: int = 0, limit: int = 50, authorization: Optional[str] = Header(None)):
    df = _leer_parquet_minio(BUCKET_APP, "dimensiones/dim_condicion.parquet")
    if df.empty:
        condiciones = [
            {"id_condicion": 1, "condicion": "Diabetes tipo 1"},
            {"id_condicion": 2, "condicion": "Diabetes tipo 2"},
            {"id_condicion": 3, "condicion": "Pre-diabetes"},
            {"id_condicion": 4, "condicion": "Sin diabetes"},
            {"id_condicion": 5, "condicion": "Hipertension"},
            {"id_condicion": 6, "condicion": "Cardiopatia"},
        ]
        df = pd.DataFrame(condiciones)
    total = len(df)
    chunk = df.iloc[skip:skip+limit]
    return {"datos": chunk.fillna("").to_dict(orient="records"), "total": total}

# ── ESTADISTICAS ──
@router.get("/estadisticas")
def estadisticas_dataset(authorization: Optional[str] = Header(None)):
    df = _leer_ultimo_parquet("stage/")
    if df.empty:
        return {"total": 0, "con_diabetes": 0, "sin_diabetes": 0, "columnas": []}
    col = next((c for c in ["diabetes", "Diabetes"] if c in df.columns), None)
    if col:
        con = int(df[col].sum())
        sin = len(df) - con
    else:
        con, sin = 0, len(df)
    return {
        "total": len(df),
        "con_diabetes": con,
        "sin_diabetes": sin,
        "columnas": list(df.columns)
    }
