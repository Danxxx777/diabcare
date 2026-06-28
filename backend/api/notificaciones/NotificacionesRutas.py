from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from utilidades.Dependencias import require_modulo
from servicios.notificaciones.NotificacionesServicio import (
    listar, crear, marcar_todas_leidas,
)

router = APIRouter(prefix="/api/notificaciones", tags=["Notificaciones"])


class NotificacionEntrada(BaseModel):
    titulo: str
    mensaje: str
    tipo: str = "info"


@router.get("/")
def listar_notificaciones(
    tipo: Optional[str] = None,
    payload: dict = Depends(require_modulo("notificaciones")),
):
    return listar(tipo)


@router.post("/")
def crear_notificacion(
    datos: NotificacionEntrada,
    payload: dict = Depends(require_modulo("notificaciones")),
):
    return crear(datos.titulo, datos.mensaje, datos.tipo)


@router.post("/marcar-leidas")
def marcar_leidas(payload: dict = Depends(require_modulo("notificaciones"))):
    return marcar_todas_leidas()
