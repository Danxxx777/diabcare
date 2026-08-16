from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from nucleo.utilidades.Dependencias import require_modulo
from paquetes.comorbilidades import ComorbilidadesServicio as S

router = APIRouter(prefix="/api/comorbilidades", tags=["P3-ext Comorbilidades"])

def _u(p): return p.get("correo") or p.get("email") or p.get("sub") or "sistema"
def _ok(r):
    if r.get("error"): raise HTTPException(400, detail=r["error"])
    return r
def _nf(r):
    if r.get("error"): raise HTTPException(404, detail=r["error"])
    return r

class ComIn(BaseModel):
    id_paciente: str
    tipo: str
    fecha_deteccion: str
    id_medico: str = ""
    notas: str = ""
    estado: str = "activa"

@router.get("")
@router.get("/")
def listar(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("comorbilidades"))):
    return S.listar_enriquecido(
        offset=offset, limit=limit, q=q,
        q_campos=["tipo", "id_paciente", "notas"],
        incluir_inactivos=True,
    )

@router.get("/resumen")
def resumen(payload=Depends(require_modulo("comorbilidades"))):
    return S.resumen_operativo()

@router.get("/paciente/{id_paciente}")
def por_paciente(id_paciente: str, payload=Depends(require_modulo("comorbilidades"))):
    res = S.comorbilidades.listar(limit=200, filtros={"id_paciente": id_paciente}, incluir_inactivos=True)
    res["comorbilidades"] = S.enriquecer(res.get("comorbilidades") or [])
    return res

@router.get("/{id_comorbilidad}")
def obtener(id_comorbilidad: str, payload=Depends(require_modulo("comorbilidades"))):
    r = _nf(S.comorbilidades.obtener(id_comorbilidad))
    enriq = S.enriquecer([r])
    return enriq[0] if enriq else r

@router.post("")
@router.post("/")
def crear(d: ComIn, payload=Depends(require_modulo("comorbilidades"))):
    data = d.dict()
    if not data.get("id_medico"):
        data["id_medico"] = str(payload.get("sub") or "")
    r = _ok(S.crear(data))
    S.comorbilidades.auditar(_u(payload), "create", f"Comorbilidad {r.get('id_comorbilidad')}", "comorbilidades")
    return r

@router.put("/{id_comorbilidad}")
def actualizar(id_comorbilidad: str, d: ComIn, payload=Depends(require_modulo("comorbilidades"))):
    r = _nf(S.comorbilidades.actualizar(id_comorbilidad, d.dict(exclude_none=True)))
    S.comorbilidades.auditar(_u(payload), "update", f"Comorbilidad {id_comorbilidad}", "comorbilidades")
    return r

@router.delete("/{id_comorbilidad}")
def eliminar(id_comorbilidad: str, payload=Depends(require_modulo("comorbilidades"))):
    r = _nf(S.comorbilidades.eliminar_logico(id_comorbilidad))
    S.comorbilidades.auditar(_u(payload), "delete", f"Comorbilidad {id_comorbilidad}", "comorbilidades")
    return r
