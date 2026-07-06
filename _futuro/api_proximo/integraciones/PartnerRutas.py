"""CU-O13 — API pública para partners (autenticación X-API-Key)."""

from fastapi import APIRouter, Depends

from utilidades.Dependencias import require_partner_key
from servicios.integraciones.IntegracionesServicio import (
    datos_partner_resumen, datos_partner_prevalencia,
)
from servicios.prediccion.PrediccionServicio import modelo_disponible, obtener_metricas

router = APIRouter(prefix="/api/partner/v1", tags=["Partner API"])


@router.get("/resumen")
def resumen(_: dict = Depends(require_partner_key)):
    return {**datos_partner_resumen(), "cu_o": "CU-O13", "oo": "OO2.1.1"}


@router.get("/prevalencia")
def prevalencia(_: dict = Depends(require_partner_key)):
    return {"datos": datos_partner_prevalencia(), "cu_o": "CU-O13", "oo": "OO2.1.1"}


@router.get("/modelo")
def modelo(_: dict = Depends(require_partner_key)):
    if not modelo_disponible():
        return {"disponible": False, "cu_o": "CU-O13"}
    return {"disponible": True, "metricas": obtener_metricas(), "cu_o": "CU-O13", "oo": "OO2.1.1"}
