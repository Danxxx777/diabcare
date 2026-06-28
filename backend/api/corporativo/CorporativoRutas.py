from fastapi import APIRouter, Depends

from utilidades.Dependencias import require_auth, require_admin
from servicios.corporativo.CorporativoServicio import obtener, actualizar

router = APIRouter(prefix="/api/corporativo", tags=["Corporativo"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


@router.get("/")
def obtener_info(payload: dict = Depends(require_auth)):
    return obtener()


@router.put("/")
def actualizar_info(datos: dict, payload: dict = Depends(require_admin)):
    return actualizar(datos, _usuario(payload))
