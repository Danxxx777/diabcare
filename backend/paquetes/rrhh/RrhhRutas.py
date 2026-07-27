from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from nucleo.utilidades.Dependencias import require_modulo, require_escritura
from paquetes.rrhh import RrhhServicio as S

router = APIRouter(prefix="/api/rrhh", tags=["P20 RRHH"])

def _u(p): return p.get("correo") or p.get("email") or p.get("sub") or "sistema"
def _ok(r):
    if r.get("error"): raise HTTPException(400, detail=r["error"])
    return r
def _nf(r):
    if r.get("error"): raise HTTPException(404, detail=r["error"])
    return r

class CargoIn(BaseModel):
    nombre: str = ""
    activo: Optional[bool] = True

class TurnoIn(BaseModel):
    nombre: str = ""
    hora_inicio: str = ""
    hora_fin: str = ""
    activo: Optional[bool] = True

class PersonalIn(BaseModel):
    id_personal: str
    id_cargo: str
    costo_hora: float = 0
    fecha_vigencia: str = ""
    activo: Optional[bool] = True

@router.get("/colaboradores")
def colaboradores(payload=Depends(require_modulo("rrhh"))):
    """Catálogo legible de personal (sin pedir IDs a mano en UI)."""
    from paquetes.usuarios.UsuariosServicio import obtener_usuarios
    rows = obtener_usuarios()
    if isinstance(rows, list):
        return {
            "colaboradores": [
                {
                    "id": u.get("id"),
                    "nombre": u.get("nombre") or u.get("email") or "Usuario",
                    "rol": u.get("rol") or "",
                    "activo": u.get("activo", True),
                }
                for u in rows
                if str(u.get("activo", True)).lower() not in ("false", "0", "no")
            ]
        }
    return {"colaboradores": []}


@router.get("/cargos")
def list_cargos(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("rrhh"))):
    return S.cargos.listar(offset, limit, incluir_inactivos=True)

@router.get("/cargos/{id_cargo}")
def get_cargo(id_cargo: str, payload=Depends(require_modulo("rrhh"))):
    return _nf(S.cargos.obtener(id_cargo))

@router.post("/cargos")
def post_cargo(d: CargoIn, payload=Depends(require_escritura("rrhh"))):
    r = _ok(S.cargos.crear(d.dict()))
    S.cargos.auditar(_u(payload), "create", f"Cargo {r.get('id_cargo')}", "rrhh"); return r

@router.put("/cargos/{id_cargo}")
def put_cargo(id_cargo: str, d: CargoIn, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.cargos.actualizar(id_cargo, d.dict(exclude_none=True)))
    S.cargos.auditar(_u(payload), "update", f"Cargo {id_cargo}", "rrhh"); return r

@router.delete("/cargos/{id_cargo}")
def del_cargo(id_cargo: str, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.cargos.eliminar_logico(id_cargo))
    S.cargos.auditar(_u(payload), "delete", f"Cargo {id_cargo}", "rrhh"); return r

@router.get("/turnos")
def list_turnos(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("rrhh"))):
    return S.turnos.listar(offset, limit, incluir_inactivos=True)

@router.get("/turnos/{id_turno}")
def get_turno(id_turno: str, payload=Depends(require_modulo("rrhh"))):
    return _nf(S.turnos.obtener(id_turno))

@router.post("/turnos")
def post_turno(d: TurnoIn, payload=Depends(require_escritura("rrhh"))):
    r = _ok(S.turnos.crear(d.dict()))
    S.turnos.auditar(_u(payload), "create", f"Turno {r.get('id_turno')}", "rrhh"); return r

@router.put("/turnos/{id_turno}")
def put_turno(id_turno: str, d: TurnoIn, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.turnos.actualizar(id_turno, d.dict(exclude_none=True)))
    S.turnos.auditar(_u(payload), "update", f"Turno {id_turno}", "rrhh"); return r

@router.delete("/turnos/{id_turno}")
def del_turno(id_turno: str, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.turnos.eliminar_logico(id_turno))
    S.turnos.auditar(_u(payload), "delete", f"Turno {id_turno}", "rrhh"); return r

@router.get("/personal")
def list_per(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("rrhh"))):
    return S.personal.listar(offset, limit, incluir_inactivos=True)

@router.get("/personal/{id_personal_costo}")
def get_per(id_personal_costo: str, payload=Depends(require_modulo("rrhh"))):
    return _nf(S.personal.obtener(id_personal_costo))

@router.post("/personal")
def post_per(d: PersonalIn, payload=Depends(require_escritura("rrhh"))):
    r = _ok(S.personal.crear(d.dict()))
    S.personal.auditar(_u(payload), "create", f"Personal {r.get('id_personal_costo')}", "rrhh"); return r

@router.put("/personal/{id_personal_costo}")
def put_per(id_personal_costo: str, d: PersonalIn, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.personal.actualizar(id_personal_costo, d.dict(exclude_none=True)))
    S.personal.auditar(_u(payload), "update", f"Personal {id_personal_costo}", "rrhh"); return r

@router.delete("/personal/{id_personal_costo}")
def del_per(id_personal_costo: str, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.personal.eliminar_logico(id_personal_costo))
    S.personal.auditar(_u(payload), "delete", f"Personal {id_personal_costo}", "rrhh"); return r

@router.get("/costeo")
def costeo(payload=Depends(require_modulo("rrhh"))):
    return S.costeo()

@router.get("/productividad")
def prod(payload=Depends(require_modulo("rrhh"))):
    return S.productividad_resumen()

@router.post("/seed")
def seed(payload=Depends(require_escritura("rrhh"))):
    S.seed(); return {"mensaje": "seed rrhh ok"}
