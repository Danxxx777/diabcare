from fastapi import APIRouter, Depends

from utilidades.Dependencias import require_modulo
from servicios.benchmarking.BenchmarkingServicio import comparativa

router = APIRouter(prefix="/api/benchmarking", tags=["Benchmarking"])


@router.get("/")
def obtener_comparativa(payload: dict = Depends(require_modulo("benchmarking"))):
    return comparativa()
