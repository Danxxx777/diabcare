"""
tablas.py — Endpoint de consulta y visualización de tablas
"""

from fastapi import APIRouter, HTTPException, Query
from servicios.cliente_minio import get_df
from servicios.procesador_datos import TABLAS_MAP

enrutador = APIRouter()


@enrutador.get("/api/tabla/{nombre}")
def obtener_tabla(nombre: str, limit: int = Query(default=50, ge=1, le=500)):
    """Retorna las primeras `limit` filas de una tabla del modelo."""
    if nombre not in TABLAS_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Tabla no permitida. Opciones: {list(TABLAS_MAP.keys())}"
        )
    df = get_df()
    tabla = TABLAS_MAP[nombre](df)
    filas = tabla.head(limit).to_dict(orient="records")
    return {"total": len(tabla), "rows": filas}
