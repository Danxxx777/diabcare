from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.reportes.ReportesServicio import (
    generar_y_subir,
    listar_reportes,
    descargar_reporte,
)

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])


class FiltroReporte(BaseModel):
    year: Optional[int] = None
    location: Optional[str] = None
    diabetes: Optional[int] = None
    gender: Optional[str] = None
    age_min: Optional[float] = None
    age_max: Optional[float] = None


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


@router.post("/generar")
def generar(
    filtros: Optional[FiltroReporte] = None,
    payload: dict = Depends(require_modulo("reportes")),
):
    f = filtros.dict(exclude_none=True) if filtros else {}
    if (f.get("age_min") is not None and f.get("age_max") is not None
            and f["age_max"] < f["age_min"]):
        raise HTTPException(status_code=400, detail="age_max debe ser mayor o igual que age_min")
    try:
        return generar_y_subir(f, _usuario(payload))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo generar el reporte: {e}")


@router.get("/")
def listar(payload: dict = Depends(require_modulo("reportes"))):
    return {"reportes": listar_reportes()}


@router.get("/{nombre}")
def descargar(nombre: str, payload: dict = Depends(require_modulo("reportes"))):
    contenido = descargar_reporte(nombre)
    if contenido is None:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
