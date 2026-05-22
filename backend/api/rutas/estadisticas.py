"""
estadisticas.py — Endpoints de estadísticas generales y recarga del dataset
"""

from fastapi import APIRouter
from servicios.cliente_minio import get_df, limpiar_cache
from servicios.procesador_datos import (
    get_dim_paciente, get_dim_ubicacion, get_dim_raza,
    get_dim_condicion, get_fact_diabetes
)

enrutador = APIRouter()


@enrutador.api_route("/api/cargar-dataset", methods=["GET", "POST"])
def cargar_dataset():
    """Fuerza la recarga del parquet más reciente desde MinIO."""
    limpiar_cache()
    df = get_df()
    return {"ok": True, "registros": len(df), "columnas": list(df.columns)}


@enrutador.get("/api/stats")
def obtener_estadisticas():
    """Retorna el conteo de registros de cada tabla del modelo."""
    df = get_df()
    return {
        "diabetes_dataset":   len(df),
        "dim_paciente":       len(get_dim_paciente(df)),
        "dim_ubicacion":      len(get_dim_ubicacion(df)),
        "dim_raza":           len(get_dim_raza(df)),
        "dim_condicion":      len(get_dim_condicion(df)),
        "fact_diabetes":      len(get_fact_diabetes(df)),
        "total_con_diabetes": int(df["diabetes"].sum()),
        "total_sin_diabetes": int((df["diabetes"] == 0).sum()),
    }
