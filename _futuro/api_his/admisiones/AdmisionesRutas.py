from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from utilidades.Dependencias import require_modulo
from servicios.admisiones.AdmisionesServicio import listar, crear, registrar_egreso, resumen

router = APIRouter(prefix="/api/admisiones", tags=["Admisiones"])


def _usuario(payload: dict) -> str:
    return payload.get("correo") or payload.get("nombre") or "sistema"


class AdmisionEntrada(BaseModel):
    id_paciente: str
    tipo: str = "ambulatoria"
    servicio: str = "Medicina interna"
    medico_id: str = ""
    medico_nombre: str = ""
    sede: str = ""
    habitacion: str = ""
    motivo: str = Field(min_length=3)
    notas: str = ""


class EgresoEntrada(BaseModel):
    notas: str = ""


@router.get("/resumen")
def admisiones_resumen(payload: dict = Depends(require_modulo("admisiones"))):
    return resumen()


@router.get("/")
def admisiones_listar(
    q: str = "",
    tipo: str = "",
    estado: str = "",
    limit: int = Query(80, le=200),
    payload: dict = Depends(require_modulo("admisiones")),
):
    return listar(q, tipo, estado, limit)


@router.post("/")
def admision_crear(datos: AdmisionEntrada, payload: dict = Depends(require_modulo("admisiones"))):
    return crear(datos.model_dump(), usuario=_usuario(payload))


@router.post("/{id_admision}/egreso")
def admision_egreso(
    id_admision: str,
    datos: EgresoEntrada,
    payload: dict = Depends(require_modulo("admisiones")),
):
    return registrar_egreso(id_admision, datos.notas)
