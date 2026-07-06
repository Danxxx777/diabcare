import io
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from typing import Optional
from paquetes.dataset.DatasetServicio import (
    generar_y_subir, listar_archivos, eliminar_archivo, eliminar_todos, eliminar_registros,
    MAX_REGISTROS_GENERACION, UBICACIONES, GENEROS,
)
from paquetes.dataset.DatasetDwhServicio import (
    materializar_dwh, resumen_dwh, leer_hechos, leer_dimension, esquema_dwh, leer_tabla,
    compactar_stage,
)
from paquetes.dataset.DatasetTraducciones import normalizar_genero, normalizar_tabaco
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
from paquetes.configuracion.ConfiguracionAjustes import MINIO_BUCKET
from nucleo.utilidades.Dependencias import require_modulo
import pandas as pd

router = APIRouter(prefix='/api/dataset', tags=['Dataset'])

BUCKET_APP = "diabcare-app"

class GenerarEntrada(BaseModel):
    cantidad: int = Field(default=1000, ge=1, le=MAX_REGISTROS_GENERACION)
    year: int = Field(default=2025, ge=2010, le=2030)
    genero: Optional[str] = None
    ubicacion: Optional[str] = None
    edad_min: Optional[float] = Field(default=None, ge=0, le=120)
    edad_max: Optional[float] = Field(default=None, ge=0, le=120)
    prevalencia_diabetes: Optional[float] = Field(default=None, ge=0, le=1)
    perfil: str = Field(default="aleatorio", pattern="^(aleatorio|balanceado|alto_riesgo|bajo_riesgo)$")
    semilla: Optional[int] = None


class EliminarRegistrosEntrada(BaseModel):
    cantidad: int = Field(ge=1, le=10_000_000)
    desde: str = Field(default="recientes", pattern="^(recientes|antiguos)$")

# ── HELPERS ──
def _leer_parquet_minio(bucket: str, path: str) -> pd.DataFrame:
    try:
        c = get_cliente()
        obj = c.get_object(bucket, path)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame()

def _leer_ultimo_parquet(prefix: str) -> pd.DataFrame:
    """Concatena todos los parquets bajo un prefix en el bucket principal."""
    try:
        c = get_cliente()
        objetos = list(c.list_objects(MINIO_BUCKET, prefix=prefix, recursive=True))
        parquets = [o for o in objetos if o.object_name.endswith('.parquet')]
        if not parquets:
            return pd.DataFrame()
        dfs = []
        for o in parquets:
            obj = c.get_object(MINIO_BUCKET, o.object_name)
            dfs.append(pd.read_parquet(io.BytesIO(obj.read())))
        return pd.concat(dfs, ignore_index=True)
    except Exception:
        return pd.DataFrame()

def _hechos_stage_fallback(skip: int, limit: int) -> dict:
    try:
        c = get_cliente()
        objetos = list(c.list_objects(MINIO_BUCKET, prefix="stage/", recursive=True))
        parquets = sorted([o for o in objetos if o.object_name.endswith('.parquet')],
                         key=lambda o: o.last_modified, reverse=True)
        if not parquets:
            return {"datos": [], "total": 0, "skip": skip, "limit": limit, "fuente": "stage"}
        import pyarrow.parquet as pq
        total = 0
        for o in parquets:
            obj = c.get_object(MINIO_BUCKET, o.object_name)
            pf = pq.ParquetFile(io.BytesIO(obj.read()))
            total += pf.metadata.num_rows
        obj = c.get_object(MINIO_BUCKET, parquets[0].object_name)
        df = pd.read_parquet(io.BytesIO(obj.read()))
        chunk = df.iloc[skip:skip+limit]
        registros = chunk.fillna("").to_dict(orient="records")
        for r in registros:
            if "gender" in r:
                r["gender"] = normalizar_genero(r["gender"])
            if "smoking_history" in r:
                r["smoking_history"] = normalizar_tabaco(r["smoking_history"])
        return {"datos": registros, "total": total, "skip": skip, "limit": limit, "fuente": "stage"}
    except Exception:
        return {"datos": [], "total": 0, "skip": skip, "limit": limit, "fuente": "stage"}

# ── GENERAR ──
@router.post("/generar")
def generar(datos: GenerarEntrada, payload: dict = Depends(require_modulo("dataset"))):
    opts = datos.model_dump(exclude={"cantidad", "year"}, exclude_none=True)
    return generar_y_subir(datos.cantidad, datos.year, opts)


@router.get("/archivos")
def archivos(payload: dict = Depends(require_modulo("dataset"))):
    return listar_archivos()


@router.delete("/archivos")
def borrar_archivo(ruta: str = Query(..., description="Ruta completa del parquet en MinIO"),
                   payload: dict = Depends(require_modulo("dataset"))):
    return eliminar_archivo(ruta)


@router.delete("/archivos/todos")
def borrar_todos(payload: dict = Depends(require_modulo("dataset"))):
    return eliminar_todos()


@router.post("/registros/eliminar")
def borrar_registros(datos: EliminarRegistrosEntrada,
                     payload: dict = Depends(require_modulo("dataset"))):
    return eliminar_registros(datos.cantidad, datos.desde)


@router.get("/opciones-generacion")
def opciones_generacion(payload: dict = Depends(require_modulo("dataset"))):
    return {
        "generos": GENEROS,
        "ubicaciones": UBICACIONES,
        "max_registros": MAX_REGISTROS_GENERACION,
        "presets": [1000, 10000, 50000, 100000, 500000, 1_000_000, 2_000_000, 5_000_000, 10_000_000],
        "perfiles": [
            {"id": "aleatorio", "label": "Aleatorio clínico"},
            {"id": "balanceado", "label": "Balanceado"},
            {"id": "alto_riesgo", "label": "Alto riesgo metabólico"},
            {"id": "bajo_riesgo", "label": "Bajo riesgo"},
        ],
    }

# ── DWH ──
@router.post("/dwh/reconstruir")
def reconstruir_dwh(payload: dict = Depends(require_modulo("dataset"))):
    return materializar_dwh()


@router.post("/stage/compactar")
def stage_compactar(payload: dict = Depends(require_modulo("dataset"))):
    return compactar_stage()


@router.get("/dwh/resumen")
def dwh_resumen(payload: dict = Depends(require_modulo("dataset"))):
    return resumen_dwh()


@router.get("/dwh/esquema")
def dwh_esquema(payload: dict = Depends(require_modulo("dataset"))):
    return esquema_dwh()


@router.get("/dwh/tabla/{tabla_id}")
def dwh_tabla(tabla_id: str, skip: int = 0, limit: int = 50,
                payload: dict = Depends(require_modulo("dataset"))):
    return leer_tabla(tabla_id, skip, limit)

# ── HECHOS ──
@router.get("/hechos")
def listar_hechos(skip: int = 0, limit: int = 50, authorization: Optional[str] = Header(None)):
    res = leer_hechos(skip, limit)
    if res.get("total", 0) > 0:
        return res
    return _hechos_stage_fallback(skip, limit)

# ── DIMENSIONES ──
@router.get("/dimension/paciente")
def dim_paciente(skip: int = 0, limit: int = 50, authorization: Optional[str] = Header(None)):
    res = leer_dimension("paciente", skip, limit)
    if res.get("total", 0) > 0:
        return res
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
    res = leer_dimension("ubicacion", skip, limit)
    if res.get("total", 0) > 0:
        return res
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
    res = leer_dimension("raza", skip, limit)
    if res.get("total", 0) > 0:
        return res
    return {"datos": [], "total": 0}

@router.get("/dimension/condicion")
def dim_condicion(skip: int = 0, limit: int = 50, authorization: Optional[str] = Header(None)):
    res = leer_dimension("condicion", skip, limit)
    if res.get("total", 0) > 0:
        return res
    return {"datos": [], "total": 0}

@router.get("/dimension/tiempo")
def dim_tiempo(skip: int = 0, limit: int = 50, authorization: Optional[str] = Header(None)):
    res = leer_dimension("tiempo", skip, limit)
    if res.get("total", 0) > 0:
        return res
    df = _leer_ultimo_parquet("stage/")
    if not df.empty and "year" in df.columns:
        years = sorted(df["year"].dropna().unique())
        df = pd.DataFrame({"id_tiempo": range(1, len(years)+1), "year": years})
        chunk = df.iloc[skip:skip+limit]
        return {"datos": chunk.fillna("").to_dict(orient="records"), "total": len(df)}
    return {"datos": [], "total": 0}

# ── ESTADISTICAS ──
@router.get("/estadisticas")
def estadisticas_dataset(authorization: Optional[str] = Header(None)):
    try:
        import pyarrow.parquet as pq
        c = get_cliente()
        objetos = list(c.list_objects(MINIO_BUCKET, prefix="stage/", recursive=True))
        parquets = [o for o in objetos if o.object_name.endswith('.parquet')]
        if not parquets:
            return {"total": 0, "con_diabetes": 0, "sin_diabetes": 0, "columnas": []}
        total = 0
        for o in parquets:
            obj = c.get_object(MINIO_BUCKET, o.object_name)
            pf = pq.ParquetFile(io.BytesIO(obj.read()))
            total += pf.metadata.num_rows
        # Columnas y diabetes del más reciente
        ultimo = sorted(parquets, key=lambda o: o.last_modified, reverse=True)[0]
        obj = c.get_object(MINIO_BUCKET, ultimo.object_name)
        df = pd.read_parquet(io.BytesIO(obj.read()))
        col = next((c for c in ["diabetes", "Diabetes"] if c in df.columns), None)
        con = int(df[col].sum()) if col else 0
        return {
            "total": total,
            "con_diabetes": con,
            "sin_diabetes": total - con,
            "columnas": list(df.columns)
        }
    except Exception:
        return {"total": 0, "con_diabetes": 0, "sin_diabetes": 0, "columnas": []}
