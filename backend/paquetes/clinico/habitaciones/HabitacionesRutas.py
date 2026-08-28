from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from nucleo.utilidades.Dependencias import require_modulo, require_escritura
from paquetes.clinico.habitaciones import HabitacionesServicio as S

router = APIRouter(prefix="/api/habitaciones", tags=["Habitaciones"])


def _usuario(payload: dict) -> str:
    return payload.get("correo") or payload.get("sub") or payload.get("nombre") or "sistema"


def _auditar(usuario: str, tipo: str, detalle: str):
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, tipo, "habitaciones", detalle)
    except Exception:
        pass


def _ok(res: dict) -> dict:
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


class CambioEstado(BaseModel):
    estado: str
    nota: str = ""


class Asignacion(BaseModel):
    id_admision: str


class Liberacion(BaseModel):
    dar_alta: bool = False


class Traslado(BaseModel):
    origen: str
    destino: str


@router.get("/mapa")
def mapa_habitaciones(payload: dict = Depends(require_modulo("habitaciones"))):
    return S.mapa()


@router.get("/esperando")
def esperando(payload: dict = Depends(require_modulo("habitaciones"))):
    return {"esperando": S.esperando_cama()}


@router.post("/{codigo}/estado")
def cambiar_estado(
    codigo: str,
    datos: CambioEstado,
    payload: dict = Depends(require_escritura("habitaciones")),
):
    usuario = _usuario(payload)
    res = _ok(S.cambiar_estado(codigo, datos.estado, datos.nota, usuario))
    _auditar(usuario, "update", f"Cama {codigo} → {datos.estado}")
    return res


@router.post("/{codigo}/asignar")
def asignar(
    codigo: str,
    datos: Asignacion,
    payload: dict = Depends(require_escritura("habitaciones")),
):
    usuario = _usuario(payload)
    res = _ok(S.asignar(codigo, datos.id_admision, usuario))
    _auditar(usuario, "update", f"Admisión {datos.id_admision} asignada a {codigo}")
    return res


@router.post("/{codigo}/liberar")
def liberar(
    codigo: str,
    datos: Liberacion,
    payload: dict = Depends(require_escritura("habitaciones")),
):
    usuario = _usuario(payload)
    res = _ok(S.liberar(codigo, datos.dar_alta, usuario))
    _auditar(usuario, "update", f"Cama {codigo} liberada{' con alta' if datos.dar_alta else ''}")
    return res


@router.post("/traslado")
def trasladar(
    datos: Traslado,
    payload: dict = Depends(require_escritura("habitaciones")),
):
    usuario = _usuario(payload)
    res = _ok(S.trasladar(datos.origen, datos.destino, usuario))
    _auditar(usuario, "update", f"Traslado {datos.origen} → {datos.destino}")
    return res
