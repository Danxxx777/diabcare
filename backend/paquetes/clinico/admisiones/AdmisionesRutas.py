from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import date

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.clinico.admisiones.AdmisionesServicio import resumen, listar, obtener, crear, actualizar, listar_camas

router = APIRouter(prefix="/api/admisiones", tags=["Admisiones"])


def _usuario(payload: dict) -> str:
    return payload.get("correo") or payload.get("sub") or payload.get("nombre") or "sistema"


def _auditar(usuario: str, tipo: str, detalle: str):
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, tipo, "admisiones", detalle)
    except Exception:
        pass


class AdmisionEntrada(BaseModel):
    id_paciente: str
    tipo: str = "ambulatoria"
    servicio: str = "Medicina interna"
    medico_id: str = ""
    medico_nombre: str = ""
    sede: str = "Sede principal"
    habitacion: str = ""
    estado: str = "activa"
    motivo: str = ""
    fecha_ingreso: str = ""
    fecha_egreso: str = ""
    via_llegada: str = "propia"
    notas: str = ""


class AdmisionActualizar(BaseModel):
    id_paciente: Optional[str] = None
    tipo: Optional[str] = None
    servicio: Optional[str] = None
    medico_id: Optional[str] = None
    medico_nombre: Optional[str] = None
    sede: Optional[str] = None
    habitacion: Optional[str] = None
    estado: Optional[str] = None
    motivo: Optional[str] = None
    fecha_ingreso: Optional[str] = None
    fecha_egreso: Optional[str] = None
    via_llegada: Optional[str] = None
    notas: Optional[str] = None


def _validar_admision(datos: dict) -> None:
    if datos.get("tipo") not in {"ambulatoria", "urgencia", "hospitalizacion"}:
        raise HTTPException(status_code=400, detail="Seleccione un tipo de atención válido")
    if datos.get("via_llegada") not in {
        "propia", "ambulancia", "referido", "traslado_interno", "rescate", "autoridad",
    }:
        raise HTTPException(status_code=400, detail="Seleccione una vía de llegada válida")
    ingreso_txt = str(datos.get("fecha_ingreso") or "")
    egreso_txt = str(datos.get("fecha_egreso") or "")
    try:
        ingreso = date.fromisoformat(ingreso_txt) if ingreso_txt else None
        egreso = date.fromisoformat(egreso_txt) if egreso_txt else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Revise las fechas de ingreso y egreso")
    if ingreso and datos.get("estado") in {"activa", "alta"} and ingreso > date.today():
        raise HTTPException(status_code=400, detail="Una admisión activa o con alta no puede iniciar en el futuro")
    if ingreso and egreso and egreso < ingreso:
        raise HTTPException(status_code=400, detail="La fecha de egreso no puede ser anterior al ingreso")


@router.get("/resumen")
def resumen_admisiones(payload: dict = Depends(require_modulo("admisiones"))):
    return resumen()


@router.get("/camas")
def camas_admisiones(payload: dict = Depends(require_modulo("admisiones"))):
    return listar_camas()


@router.get("/")
def listar_admisiones(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    estado: str = "",
    q: str = "",
    tipo: str = "",
    payload: dict = Depends(require_modulo("admisiones")),
):
    return listar(offset, limit, estado, q, tipo)


@router.get("/{id_admision}")
def obtener_admision(id_admision: str, payload: dict = Depends(require_modulo("admisiones"))):
    res = obtener(id_admision)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/")
def crear_admision(datos: AdmisionEntrada, payload: dict = Depends(require_modulo("admisiones"))):
    contenido = datos.dict()
    _validar_admision(contenido)
    res = crear(contenido)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    _auditar(_usuario(payload), "create", f"Admisión {res.get('id_admision')}")
    return res


@router.put("/{id_admision}")
def editar_admision(
    id_admision: str,
    datos: AdmisionActualizar,
    payload: dict = Depends(require_modulo("admisiones")),
):
    cambios = datos.dict(exclude_none=True)
    actual = obtener(id_admision)
    if "error" in actual:
        raise HTTPException(status_code=404, detail=actual["error"])
    _validar_admision({**actual, **cambios})
    res = actualizar(id_admision, cambios)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    _auditar(_usuario(payload), "update", f"Admisión {id_admision}")
    return res
