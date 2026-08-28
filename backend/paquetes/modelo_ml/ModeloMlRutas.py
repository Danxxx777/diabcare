from fastapi import APIRouter, Depends

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.modelo_ml.ModeloMlServicio import info, reentrenar, historial, resumen

router = APIRouter(prefix="/api/modelo-ml", tags=["Modelo ML"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


@router.get("/info")
def obtener_info(payload: dict = Depends(require_modulo("modelo_ml"))):
    return info()


@router.get("/historial")
def obtener_historial(payload: dict = Depends(require_modulo("modelo_ml"))):
    return historial()


@router.get("/resumen")
def obtener_resumen(payload: dict = Depends(require_modulo("modelo_ml"))):
    return resumen()


@router.post("/reentrenar")
def reentrenar_modelo(payload: dict = Depends(require_modulo("modelo_ml"))):
    return reentrenar(_usuario(payload))
