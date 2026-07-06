from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from utilidades.Dependencias import require_modulo, require_partner_key
from servicios.integraciones.IntegracionesServicio import (
    estado, generar_api_key, registrar_lead, listar_leads,
    crear_pago, confirmar_pago, listar_pagos,
    estado_despliegue, ejecutar_pipeline_cicd, openapi_partner,
    datos_partner_resumen, datos_partner_prevalencia,
)
from servicios.prediccion.PrediccionServicio import modelo_disponible, obtener_metricas

router = APIRouter(prefix="/api/integraciones", tags=["Integraciones"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


class LeadEntrada(BaseModel):
    nombre: str = Field(min_length=2)
    email: str = Field(min_length=5)
    empresa: str = ""
    fuente: str = "web"


class PagoEntrada(BaseModel):
    plan: str = Field(default="profesional", pattern="^(basico|profesional|enterprise)$")
    monto: float = Field(gt=0, le=99999)
    moneda: str = "USD"


@router.get("/")
def obtener_estado(payload: dict = Depends(require_modulo("integraciones"))):
    return estado()


@router.post("/api-key")
def regenerar_api_key(payload: dict = Depends(require_modulo("integraciones"))):
    return generar_api_key(_usuario(payload))


# ── CU-O11 HubSpot ──
@router.post("/leads")
def crear_lead(datos: LeadEntrada, payload: dict = Depends(require_modulo("integraciones"))):
    return registrar_lead(datos.nombre, datos.email, datos.empresa, datos.fuente)


@router.get("/leads")
def obtener_leads(payload: dict = Depends(require_modulo("integraciones"))):
    return {"leads": listar_leads(), "cu_o": "CU-O11", "oo": "OO1.1.1"}


# ── CU-O12 Stripe ──
@router.post("/pagos")
def iniciar_pago(datos: PagoEntrada, payload: dict = Depends(require_modulo("integraciones"))):
    return crear_pago(datos.plan, datos.monto, datos.moneda)


@router.get("/pagos")
def obtener_pagos(payload: dict = Depends(require_modulo("integraciones"))):
    return {"pagos": listar_pagos(), "cu_o": "CU-O12", "oo": "OO1.2.1"}


@router.post("/pagos/{pago_id}/confirmar")
def confirmar_pago_route(pago_id: str, payload: dict = Depends(require_modulo("integraciones"))):
    return confirmar_pago(pago_id)


# ── CU-O14 OpenAPI partner ──
@router.get("/openapi-partner")
def esquema_partner():
    return openapi_partner()


# ── CU-O15 CI/CD ──
@router.get("/despliegue")
def despliegue(payload: dict = Depends(require_modulo("integraciones"))):
    return estado_despliegue()


@router.post("/despliegue/ejecutar")
def ejecutar_despliegue(payload: dict = Depends(require_modulo("integraciones"))):
    return ejecutar_pipeline_cicd(_usuario(payload))


# ── CU-O13 Partner API (también accesible vía /api/partner/v1) ──
@router.get("/partner/resumen")
def partner_resumen_integraciones(_: dict = Depends(require_partner_key)):
    return datos_partner_resumen()


@router.get("/partner/prevalencia")
def partner_prevalencia_integraciones(_: dict = Depends(require_partner_key)):
    return {"datos": datos_partner_prevalencia(), "cu_o": "CU-O13"}


@router.get("/partner/modelo")
def partner_modelo_integraciones(_: dict = Depends(require_partner_key)):
    if not modelo_disponible():
        return {"disponible": False, "mensaje": "Modelo no entrenado"}
    return {"disponible": True, "metricas": obtener_metricas()}
