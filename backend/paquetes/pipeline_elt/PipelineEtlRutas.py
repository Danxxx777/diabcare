from fastapi import APIRouter, Depends

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.pipeline_elt.PipelineEtlModelos import EjecutarPipelineEntrada
from paquetes.pipeline_elt.PipelineEtlServicio import obtener_estado, ejecutar_elt

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline ELT"])


def _usuario(payload: dict) -> str:
    return (payload.get("email") or payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


@router.get("/estado")
def estado_pipeline(payload: dict = Depends(require_modulo("pipeline_etl"))):
    return obtener_estado()


@router.post("/ejecutar")
def ejecutar_pipeline(
    datos: EjecutarPipelineEntrada | None = None,
    payload: dict = Depends(require_modulo("pipeline_etl")),
):
    historico = bool((datos or EjecutarPipelineEntrada()).historico)
    return ejecutar_elt(_usuario(payload), historico=historico)
