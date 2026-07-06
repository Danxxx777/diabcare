from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.clinico.citas.CitasServicio import listar_por_medico, actualizar_estado_medico

router = APIRouter(prefix="/api/mis-citas", tags=["Mis citas médico"])

_ID_CITA = Path(..., pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class CitaEstadoEntrada(BaseModel):
    estado: str


def _nombre(payload: dict) -> str:
    return str(payload.get("nombre") or "").strip()


def _auditar(usuario: str, detalle: str):
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "update", "mis_citas", detalle)
    except Exception:
        pass


@router.get("/")
def listar(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    fecha: str = "",
    estado: str = "",
    payload: dict = Depends(require_modulo("mis_citas")),
):
    uid = str(payload.get("sub") or "")
    return listar_por_medico(uid, offset, limit, fecha, estado, nombre_jwt=_nombre(payload))


@router.put("/{id_cita}/estado")
def cambiar_estado(
    id_cita: str = _ID_CITA,
    datos: CitaEstadoEntrada = ...,
    payload: dict = Depends(require_modulo("mis_citas")),
):
    uid = str(payload.get("sub") or "")
    res = actualizar_estado_medico(id_cita, uid, datos.estado, nombre_jwt=_nombre(payload))
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res["error"])
    user = payload.get("email") or payload.get("nombre") or uid
    _auditar(str(user), f"Cita {id_cita} → {datos.estado}")
    return res
