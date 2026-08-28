from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, validator
from typing import Optional
from datetime import date
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
    severidad: str = "moderada"
    proximo_control: Optional[str] = None

    @validator("tipo")
    def validar_tipo(cls, valor):
        if valor not in S.TIPOS:
            raise ValueError("Seleccione un tipo de complicación válido")
        return valor

    @validator("estado")
    def validar_estado(cls, valor):
        if valor not in {"activa", "controlada", "resuelta"}:
            raise ValueError("Seleccione un estado clínico válido")
        return valor

    @validator("severidad")
    def validar_severidad(cls, valor):
        if valor not in {"leve", "moderada", "severa"}:
            raise ValueError("Seleccione una severidad válida")
        return valor

    @validator("fecha_deteccion")
    def validar_deteccion(cls, valor):
        try:
            fecha = date.fromisoformat(valor)
        except ValueError:
            raise ValueError("La fecha de detección no es válida")
        if fecha > date.today():
            raise ValueError("La fecha de detección no puede estar en el futuro")
        return valor

    @validator("proximo_control")
    def validar_control(cls, valor):
        if not valor:
            return valor
        try:
            fecha = date.fromisoformat(valor)
        except ValueError:
            raise ValueError("La fecha de seguimiento no es válida")
        if fecha < date.today():
            raise ValueError("El próximo seguimiento no puede estar en el pasado")
        return valor

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
    cambios = d.dict(exclude_none=True)
    if not cambios.get("id_medico"):
        cambios.pop("id_medico", None)
    r = _nf(S.comorbilidades.actualizar(id_comorbilidad, cambios))
    S.comorbilidades.auditar(_u(payload), "update", f"Comorbilidad {id_comorbilidad}", "comorbilidades")
    return r

@router.delete("/{id_comorbilidad}")
def eliminar(id_comorbilidad: str, payload=Depends(require_modulo("comorbilidades"))):
    r = _nf(S.comorbilidades.eliminar_logico(id_comorbilidad))
    S.comorbilidades.auditar(_u(payload), "delete", f"Comorbilidad {id_comorbilidad}", "comorbilidades")
    return r
