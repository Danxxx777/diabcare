from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional

from utilidades.Dependencias import require_modulo
from servicios.citas.CitasServicio import listar, listar_hoy, crear, actualizar_estado, completar

router = APIRouter(prefix="/api/citas", tags=["Agenda"])


def _usuario(payload: dict) -> str:
    return payload.get("correo") or payload.get("sub") or payload.get("nombre") or "sistema"


class CitaEntrada(BaseModel):
    id_paciente: str
    fecha: str
    hora: str = "09:00"
    motivo: str = "Consulta de control"
    sede: str = ""
    notas: str = ""


class EstadoEntrada(BaseModel):
    estado: str
    notas: str = ""


class CompletarEntrada(BaseModel):
    notas: str = ""
    programar_seguimiento: bool = True


@router.get("/hoy")
def citas_hoy(fecha: str = "", payload: dict = Depends(require_modulo("citas"))):
    return listar_hoy(fecha or None)


@router.get("/")
def citas_listar(
    fecha: str = "",
    estado: str = "",
    id_paciente: str = "",
    limit: int = Query(100, le=300),
    payload: dict = Depends(require_modulo("citas")),
):
    return listar(fecha, estado, id_paciente, limit)


@router.post("/")
def cita_crear(datos: CitaEntrada, payload: dict = Depends(require_modulo("citas"))):
    return crear(datos.model_dump(), medico=_usuario(payload))


@router.patch("/{id_cita}/estado")
def cita_estado(id_cita: str, datos: EstadoEntrada, payload: dict = Depends(require_modulo("citas"))):
    return actualizar_estado(id_cita, datos.estado, datos.notas)


@router.post("/{id_cita}/completar")
def cita_completar(id_cita: str, datos: CompletarEntrada, payload: dict = Depends(require_modulo("citas"))):
    return completar(id_cita, datos.notas, datos.programar_seguimiento)
