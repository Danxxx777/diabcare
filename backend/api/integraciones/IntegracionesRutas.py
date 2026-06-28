from fastapi import APIRouter, Depends

from utilidades.Dependencias import require_modulo
from servicios.integraciones.IntegracionesServicio import estado, generar_api_key

router = APIRouter(prefix="/api/integraciones", tags=["Integraciones"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


@router.get("/")
def obtener_estado(payload: dict = Depends(require_modulo("integraciones"))):
    return estado()


@router.post("/api-key")
def regenerar_api_key(payload: dict = Depends(require_modulo("integraciones"))):
    return generar_api_key(_usuario(payload))
