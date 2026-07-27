from fastapi import APIRouter, Depends, Query
from typing import Optional

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.auditoria.AuditoriaServicio import listar, estadisticas

router = APIRouter(prefix="/api/auditoria", tags=["Auditoria"])


@router.get("/")
def listar_eventos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    tipo: Optional[str] = None,
    usuario: Optional[str] = None,
    modulo: Optional[str] = None,
    resultado: Optional[str] = None,
    payload: dict = Depends(require_modulo("auditoria")),
):
    return listar(
        skip=skip, limit=limit, tipo=tipo,
        usuario=usuario, modulo=modulo, resultado=resultado,
    )


@router.get("/estadisticas")
def stats(payload: dict = Depends(require_modulo("auditoria"))):
    return estadisticas()
