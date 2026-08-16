from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from nucleo.utilidades.Dependencias import require_modulo
from paquetes.laboratorio import LaboratorioServicio as S

router = APIRouter(prefix="/api/laboratorio", tags=["P18 Laboratorio"])

def _u(p): return p.get("correo") or p.get("email") or p.get("sub") or "sistema"
def _ok(r):
    if r.get("error"): raise HTTPException(400, detail=r["error"])
    return r
def _nf(r):
    if r.get("error"): raise HTTPException(404, detail=r["error"])
    return r

class PruebaIn(BaseModel):
    codigo: str = ""
    nombre: str = ""
    unidad: str = ""
    activo: Optional[bool] = True

class OrdenIn(BaseModel):
    id_paciente: str
    id_prueba: str
    id_medico: str = ""
    encounter_id: str = ""
    estado: str = "pendiente"
    fecha: str = ""

class ResultadoIn(BaseModel):
    valor: str = ""
    unidad: str = ""
    fecha: str = ""
    estado: str = "registrado"

@router.get("/resumen")
def resumen(payload=Depends(require_modulo("laboratorio"))):
    return S.resumen_operativo()

@router.get("/pruebas")
def list_pr(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("laboratorio"))):
    return S.pruebas.listar(offset, limit, q=q, q_campos=["codigo", "nombre"], incluir_inactivos=True)

@router.get("/pruebas/{id_prueba}")
def get_pr(id_prueba: str, payload=Depends(require_modulo("laboratorio"))):
    return _nf(S.pruebas.obtener(id_prueba))

@router.post("/pruebas")
def post_pr(d: PruebaIn, payload=Depends(require_modulo("laboratorio_ordenar"))):
    r = _ok(S.pruebas.crear(d.dict()))
    S.pruebas.auditar(_u(payload), "create", f"Prueba {r.get('id_prueba')}", "laboratorio"); return r

@router.put("/pruebas/{id_prueba}")
def put_pr(id_prueba: str, d: PruebaIn, payload=Depends(require_modulo("laboratorio_ordenar"))):
    r = _nf(S.pruebas.actualizar(id_prueba, d.dict(exclude_none=True)))
    S.pruebas.auditar(_u(payload), "update", f"Prueba {id_prueba}", "laboratorio"); return r

@router.delete("/pruebas/{id_prueba}")
def del_pr(id_prueba: str, payload=Depends(require_modulo("laboratorio_ordenar"))):
    r = _nf(S.pruebas.eliminar_logico(id_prueba))
    S.pruebas.auditar(_u(payload), "delete", f"Prueba {id_prueba}", "laboratorio"); return r

@router.get("/ordenes")
def list_or(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("laboratorio"))):
    return S.listar_ordenes(offset=offset, limit=limit, q=q, incluir_inactivos=True)

@router.get("/ordenes/{id_orden}")
def get_or(id_orden: str, payload=Depends(require_modulo("laboratorio"))):
    r = _nf(S.ordenes.obtener(id_orden))
    enriq = S.enriquecer([r], estados=S.ESTADOS_ORDEN)
    return enriq[0] if enriq else r

@router.post("/ordenes")
def post_or(d: OrdenIn, payload=Depends(require_modulo("laboratorio_ordenar"))):
    data = d.dict()
    data.setdefault("id_medico", payload.get("sub") or "")
    data["estado"] = "pendiente"
    if not data.get("fecha"):
        from datetime import date
        data["fecha"] = date.today().isoformat()
    r = _ok(S.ordenes.crear(data))
    S.ordenes.auditar(_u(payload), "create", f"Orden {r.get('id_orden')}", "laboratorio"); return r

@router.put("/ordenes/{id_orden}")
def put_or(id_orden: str, d: OrdenIn, payload=Depends(require_modulo("laboratorio_ordenar"))):
    r = _nf(S.ordenes.actualizar(id_orden, d.dict(exclude_none=True)))
    S.ordenes.auditar(_u(payload), "update", f"Orden {id_orden}", "laboratorio"); return r

@router.delete("/ordenes/{id_orden}")
def del_or(id_orden: str, payload=Depends(require_modulo("laboratorio_ordenar"))):
    r = _nf(S.ordenes.eliminar_logico(id_orden))
    S.ordenes.auditar(_u(payload), "delete", f"Orden {id_orden}", "laboratorio"); return r

@router.put("/ordenes/{id_orden}/resultado")
def put_res(id_orden: str, d: ResultadoIn, payload=Depends(require_modulo("laboratorio_resultado"))):
    r = _ok(S.cargar_resultado(id_orden, d.dict()))
    S.resultados.auditar(_u(payload), "create", f"Resultado orden {id_orden}", "laboratorio"); return r

@router.get("/resultados")
def list_res(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("laboratorio"))):
    return S.listar_resultados(offset=offset, limit=limit, q=q, incluir_inactivos=True)

@router.get("/resultados/{id_resultado}")
def get_res(id_resultado: str, payload=Depends(require_modulo("laboratorio"))):
    r = _nf(S.resultados.obtener(id_resultado))
    enriq = S.enriquecer([r], estados=S.ESTADOS_RESULTADO)
    return enriq[0] if enriq else r

@router.put("/resultados/{id_resultado}")
def put_res_id(id_resultado: str, d: ResultadoIn, payload=Depends(require_modulo("laboratorio_resultado"))):
    r = _nf(S.resultados.actualizar(id_resultado, d.dict(exclude_none=True)))
    S.resultados.auditar(_u(payload), "update", f"Resultado {id_resultado}", "laboratorio"); return r

@router.delete("/resultados/{id_resultado}")
def del_res(id_resultado: str, payload=Depends(require_modulo("laboratorio_resultado"))):
    r = _nf(S.resultados.eliminar_logico(id_resultado))
    S.resultados.auditar(_u(payload), "delete", f"Resultado {id_resultado}", "laboratorio"); return r

@router.post("/seed")
def seed(payload=Depends(require_modulo("laboratorio_ordenar"))):
    S.seed(); return {"mensaje": "seed laboratorio ok"}
