from fastapi import APIRouter, Depends

from utilidades.Dependencias import require_modulo
from servicios.configuracion.ConfiguracionServicio import (
    obtener_configuracion,
    guardar_configuracion,
)

router = APIRouter(prefix="/api/configuracion", tags=["Configuracion"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


@router.get("/")
def obtener(payload: dict = Depends(require_modulo("configuracion"))):
    return obtener_configuracion()


@router.post("/")
def guardar(datos: dict, payload: dict = Depends(require_modulo("configuracion"))):
    return guardar_configuracion(datos, _usuario(payload))
