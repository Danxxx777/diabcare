from fastapi import APIRouter, Depends

from utilidades.Dependencias import require_admin
from servicios.sistema.SistemaServicio import preparar_clinica

router = APIRouter(prefix="/api/sistema", tags=["Sistema"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


@router.post("/preparar-clinica")
def preparar(payload: dict = Depends(require_admin)):
    """Materializa DWH, integraciones y alertas para dejar la clínica operativa."""
    return preparar_clinica(_usuario(payload))
