from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, validator
from typing import Optional
from nucleo.utilidades.Dependencias import require_modulo
from paquetes.urgencias import UrgenciasServicio as S

router = APIRouter(prefix="/api/urgencias", tags=["P19 Urgencias"])

def _u(p): return p.get("correo") or p.get("email") or p.get("sub") or "sistema"
def _ok(r):
    if r.get("error"): raise HTTPException(400, detail=r["error"])
    return r
def _nf(r):
    if r.get("error"): raise HTTPException(404, detail=r["error"])
    return r

class UrgenciaIn(BaseModel):
    id_paciente: str
    triage: str = "III"
    motivo: str = ""
    via_llegada: str = "propia"
    hora_llegada: str = ""
    desenlace: str = "en_espera"
    estado: str = "triage"

    @validator("id_paciente", "motivo")
    def validar_texto_obligatorio(cls, valor):
        if not str(valor or "").strip():
            raise ValueError("Este campo es obligatorio")
        return str(valor).strip()

    @validator("triage")
    def validar_triage(cls, valor):
        valor = str(valor or "").upper()
        if valor not in {"I", "II", "III", "IV", "V"}:
            raise ValueError("Seleccione una prioridad de triage válida")
        return valor

    @validator("via_llegada")
    def validar_via_llegada(cls, valor):
        if valor not in S.VIAS_LLEGADA:
            raise ValueError("Seleccione una vía de llegada válida")
        return valor

class AtenderIn(BaseModel):
    desenlace: str = "alta"
    motivo: Optional[str] = None

@router.get("/resumen")
def resumen(payload=Depends(require_modulo("urgencias"))):
    return S.resumen_operativo()

@router.get("")
@router.get("/")
def listar(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("urgencias"))):
    return S.listar_enriquecido(
        offset=offset, limit=limit, q=q,
        q_campos=["motivo", "id_paciente", "triage", "estado", "desenlace"],
        incluir_inactivos=True,
    )

@router.get("/{id_urgencia}")
def obtener(id_urgencia: str, payload=Depends(require_modulo("urgencias"))):
    r = _nf(S.urgencias.obtener(id_urgencia))
    enriq = S.enriquecer([r])
    return enriq[0] if enriq else r

@router.post("")
@router.post("/")
def crear(d: UrgenciaIn, payload=Depends(require_modulo("urgencias_triage"))):
    r = _ok(S.crear_triage(d.dict(), str(payload.get("sub") or "")))
    S.urgencias.auditar(_u(payload), "create", f"Urgencia {r.get('id_urgencia')}", "urgencias"); return r

@router.put("/{id_urgencia}")
def actualizar(id_urgencia: str, d: UrgenciaIn, payload=Depends(require_modulo("urgencias_triage"))):
    r = _nf(S.urgencias.actualizar(id_urgencia, d.dict(exclude_none=True)))
    S.urgencias.auditar(_u(payload), "update", f"Urgencia {id_urgencia}", "urgencias"); return r

@router.put("/{id_urgencia}/atender")
def atender(id_urgencia: str, d: AtenderIn, payload=Depends(require_modulo("urgencias_atender"))):
    r = _ok(S.atender(id_urgencia, str(payload.get("sub") or ""), d.dict()))
    S.urgencias.auditar(_u(payload), "update", f"Atender {id_urgencia}", "urgencias"); return r

@router.delete("/{id_urgencia}")
def eliminar(id_urgencia: str, payload=Depends(require_modulo("urgencias_triage"))):
    r = _nf(S.urgencias.eliminar_logico(id_urgencia))
    S.urgencias.auditar(_u(payload), "delete", f"Urgencia {id_urgencia}", "urgencias"); return r
