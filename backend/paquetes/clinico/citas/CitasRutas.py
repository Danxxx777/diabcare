from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from typing import Optional

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.clinico.citas.CitasServicio import (
    hoy, listar, listar_por_medico, obtener, crear, actualizar, cancelar, actualizar_estado_medico,
)

router = APIRouter(prefix="/api/citas", tags=["Agenda clínica"])

_ID_CITA = Path(..., pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _usuario(payload: dict) -> str:
    return payload.get("correo") or payload.get("email") or payload.get("sub") or payload.get("nombre") or "sistema"


def _nombre(payload: dict) -> str:
    return str(payload.get("nombre") or "").strip()


def _auditar(usuario: str, tipo: str, detalle: str):
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, tipo, "citas", detalle)
    except Exception:
        pass


class CitaEntrada(BaseModel):
    id_paciente: str
    medico: str = ""
    fecha: str = ""
    hora: str = "09:00"
    estado: str = "programada"
    motivo: str = "Control clínico"
    sede: str = "Sede principal"
    notas: str = ""
    proximo_control: str = ""


class CitaActualizar(BaseModel):
    id_paciente: Optional[str] = None
    medico: Optional[str] = None
    fecha: Optional[str] = None
    hora: Optional[str] = None
    estado: Optional[str] = None
    motivo: Optional[str] = None
    sede: Optional[str] = None
    notas: Optional[str] = None
    proximo_control: Optional[str] = ""


class CitaEstadoMedico(BaseModel):
    estado: str


@router.get("/hoy")
def citas_hoy(payload: dict = Depends(require_modulo("citas"))):
    return hoy()


@router.get("/mis-citas")
def mis_citas(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    fecha: str = "",
    estado: str = "",
    payload: dict = Depends(require_modulo("mis_citas")),
):
    uid = str(payload.get("sub") or "")
    return listar_por_medico(uid, offset, limit, fecha, estado, nombre_jwt=_nombre(payload))


@router.get("/")
def listar_citas(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    fecha: str = "",
    estado: str = "",
    q: str = "",
    payload: dict = Depends(require_modulo("citas")),
):
    return listar(offset, limit, fecha, estado, q)


@router.put("/{id_cita}/estado")
def estado_cita_medico(
    id_cita: str = _ID_CITA,
    datos: CitaEstadoMedico = ...,
    payload: dict = Depends(require_modulo("mis_citas")),
):
    uid = str(payload.get("sub") or "")
    res = actualizar_estado_medico(id_cita, uid, datos.estado, nombre_jwt=_nombre(payload))
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res["error"])
    _auditar(_usuario(payload), "update", f"Cita {id_cita} → {datos.estado}")
    return res


@router.get("/{id_cita}")
def obtener_cita(id_cita: str = _ID_CITA, payload: dict = Depends(require_modulo("citas"))):
    res = obtener(id_cita)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/")
def crear_cita(datos: CitaEntrada, payload: dict = Depends(require_modulo("citas"))):
    res = crear(datos.dict())
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    _auditar(_usuario(payload), "create", f"Cita {res.get('id_cita')}")
    return res


@router.put("/{id_cita}")
def editar_cita(
    id_cita: str = _ID_CITA,
    datos: CitaActualizar = ...,
    payload: dict = Depends(require_modulo("citas")),
):
    res = actualizar(id_cita, datos.dict(exclude_none=True))
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    _auditar(_usuario(payload), "update", f"Cita {id_cita}")
    return res


@router.delete("/{id_cita}")
def cancelar_cita(id_cita: str = _ID_CITA, payload: dict = Depends(require_modulo("citas"))):
    res = cancelar(id_cita)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    _auditar(_usuario(payload), "delete", f"Cita {id_cita} cancelada")
    return res
