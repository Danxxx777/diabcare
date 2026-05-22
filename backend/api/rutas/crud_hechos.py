"""
crud_hechos.py — Endpoints CRUD para la tabla de hechos fact_diabetes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from servicios.cliente_minio import get_df
import servicios.cliente_minio as cache
import pandas as pd

enrutador = APIRouter()


class RegistroHecho(BaseModel):
    year: int
    gender: str
    age: float
    location: str
    hypertension: int
    heart_disease: int
    smoking_history: str
    bmi: float
    hbA1c_level: float
    blood_glucose_level: int
    diabetes: int


@enrutador.post("/api/fact")
def crear_hecho(registro: RegistroHecho):
    """Agrega un nuevo registro al dataset en memoria."""
    df = get_df()
    nuevo = pd.DataFrame([registro.dict()])
    cache._df_cache = pd.concat([df, nuevo], ignore_index=True)
    nuevo_id = len(cache._df_cache) - 1
    return {"ok": True, "id": nuevo_id, "registro": registro.dict()}


@enrutador.get("/api/fact/{id_fact}")
def obtener_hecho(id_fact: int):
    """Retorna el registro en la posición id_fact del dataset."""
    df = get_df()
    if id_fact < 0 or id_fact >= len(df):
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return df.iloc[id_fact].to_dict()


@enrutador.put("/api/fact/{id_fact}")
def actualizar_hecho(
    id_fact: int,
    bmi: float = None,
    hbA1c_level: float = None,
    blood_glucose_level: int = None,
    diabetes: int = None
):
    df = get_df()
    if id_fact < 0 or id_fact >= len(df):
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    if bmi is not None:
        cache._df_cache.iloc[id_fact, cache._df_cache.columns.get_loc("bmi")] = bmi
    if hbA1c_level is not None:
        cache._df_cache.iloc[id_fact, cache._df_cache.columns.get_loc("hbA1c_level")] = hbA1c_level
    if blood_glucose_level is not None:
        cache._df_cache.iloc[id_fact, cache._df_cache.columns.get_loc("blood_glucose_level")] = blood_glucose_level
    if diabetes is not None:
        cache._df_cache.iloc[id_fact, cache._df_cache.columns.get_loc("diabetes")] = diabetes
    return {"ok": True, "registro": cache._df_cache.iloc[id_fact].to_dict()}


@enrutador.delete("/api/fact/{id_fact}")
def eliminar_hecho(id_fact: int):
    """Elimina el registro en la posición id_fact y reindexea el DataFrame."""
    df = get_df()
    if id_fact < 0 or id_fact >= len(df):
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    cache._df_cache = df.drop(index=id_fact).reset_index(drop=True)
    return {"ok": True, "registros_restantes": len(cache._df_cache)}