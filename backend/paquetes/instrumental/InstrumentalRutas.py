from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.instrumental import InstrumentalServicio as S

router = APIRouter(prefix="/api/instrumental", tags=["Instrumental hospitalario"])


class InstrumentalEntrada(BaseModel):
    codigo: str = ""
    nombre: str
    tipo: str = "instrumental"
    serie: str = ""
    ubicacion: str = "Almacén clínico"
    existencia: int = 1
    notas: str = ""


class TransicionEntrada(BaseModel):
    responsable: str = ""
    ubicacion: str = ""
    detalle: str = ""
    id_admision: str = ""


def _ok(resultado: dict, codigo: int = 400) -> dict:
    if resultado.get("error"):
        raise HTTPException(status_code=codigo, detail=resultado["error"])
    return resultado


@router.get("/")
def listar(offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), q: str = "", estado: str = "", payload: dict = Depends(require_modulo("instrumental"))):
    return S.listar(offset, limit, q, estado)


@router.post("/")
def crear(datos: InstrumentalEntrada, payload: dict = Depends(require_modulo("instrumental"))):
    return _ok(S.crear(datos.model_dump()))


@router.get("/asignados/admision/{id_admision}")
def asignados_admision(id_admision: str, payload: dict = Depends(require_modulo("instrumental"))):
    return S.asignados_admision(id_admision)


@router.get("/{id_instrumental}")
def obtener(id_instrumental: str, payload: dict = Depends(require_modulo("instrumental"))):
    return _ok(S.instrumentos.obtener(id_instrumental), 404)


@router.post("/{id_instrumental}/{accion}")
def transicionar(id_instrumental: str, accion: str, datos: TransicionEntrada, payload: dict = Depends(require_modulo("instrumental"))):
    return _ok(S.transicionar(id_instrumental, accion, datos.model_dump()))


@router.get("/{id_instrumental}/movimientos/historial")
def historial(id_instrumental: str, payload: dict = Depends(require_modulo("instrumental"))):
    return S.historial(id_instrumental)
