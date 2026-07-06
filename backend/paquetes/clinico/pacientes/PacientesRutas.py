from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Header
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from nucleo.utilidades.Dependencias import require_modulo, _extraer_token, PERMISOS_MODULOS
from paquetes.clinico.pacientes.PacientesServicio import (
    resumen, listar, obtener, crear, actualizar, desactivar,
)
from paquetes.registros_clinicos.RegistrosClinicosServicio import listar_por_paciente

router = APIRouter(prefix="/api/pacientes", tags=["Pacientes"])


def _usuario(payload: dict) -> str:
    return payload.get("correo") or payload.get("sub") or payload.get("nombre") or "sistema"


def _auditar(usuario: str, tipo: str, detalle: str):
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, tipo, "pacientes", detalle)
    except Exception:
        pass


def _auth_foto(
    authorization: str = Header(None),
    token: str = Query(None),
) -> dict:
    """JWT por cabecera Authorization o ?token= (necesario para <img src>)."""
    raw = (authorization or "").replace("Bearer ", "").strip() or (token or "").strip()
    if not raw:
        raise HTTPException(status_code=401, detail="Token requerido")
    payload = _extraer_token(raw)
    roles = PERMISOS_MODULOS.get("pacientes", ["administrador"])
    if payload.get("rol") not in roles:
        raise HTTPException(status_code=403, detail="Sin acceso al módulo pacientes")
    return payload


class PacienteEntrada(BaseModel):
    nombre: str
    apellido: str = ""
    documento: str = ""
    edad: float = 0
    genero: str = "Femenino"
    telefono: str = ""
    email: str = ""
    sede: str = "Sede principal"
    notas: str = ""
    codigo: Optional[str] = None


class PacienteActualizar(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    documento: Optional[str] = None
    edad: Optional[float] = None
    genero: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    sede: Optional[str] = None
    estado: Optional[str] = None
    notas: Optional[str] = None


@router.get("/resumen")
def resumen_pacientes(payload: dict = Depends(require_modulo("pacientes"))):
    return resumen()


@router.get("/")
def listar_pacientes(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: str = "",
    estado: str = "",
    payload: dict = Depends(require_modulo("pacientes")),
):
    return listar(offset, limit, q, estado)


@router.get("/{id_paciente}/consultas")
def consultas_paciente(
    id_paciente: str,
    limit: int = Query(50, ge=1, le=200),
    payload: dict = Depends(require_modulo("pacientes")),
):
    p = obtener(id_paciente)
    if "error" in p:
        raise HTTPException(status_code=404, detail=p["error"])
    return listar_por_paciente(id_paciente, limit)


@router.get("/{id_paciente}/foto")
def foto_paciente(id_paciente: str, payload: dict = Depends(_auth_foto)):
    from paquetes.clinico.pacientes.FotosEntidadServicio import leer_bytes_foto

    p = obtener(id_paciente)
    if "error" in p:
        raise HTTPException(status_code=404, detail=p["error"])
    res = leer_bytes_foto("paciente", id_paciente)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res["error"])
    return Response(content=res["contenido"], media_type=res["mime_type"])


@router.post("/{id_paciente}/foto")
async def subir_foto_paciente(
    id_paciente: str,
    archivo: UploadFile = File(...),
    payload: dict = Depends(require_modulo("pacientes")),
):
    from paquetes.clinico.pacientes.FotosEntidadServicio import guardar_foto

    p = obtener(id_paciente)
    if "error" in p:
        raise HTTPException(status_code=404, detail=p["error"])
    contenido = await archivo.read()
    res = guardar_foto(
        "paciente",
        id_paciente,
        contenido,
        archivo.content_type or "image/jpeg",
        _usuario(payload),
    )
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res["error"])
    _auditar(_usuario(payload), "update", f"Foto paciente {id_paciente}")
    return res


@router.get("/{id_paciente}")
def obtener_paciente(id_paciente: str, payload: dict = Depends(require_modulo("pacientes"))):
    res = obtener(id_paciente)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/")
def crear_paciente(datos: PacienteEntrada, payload: dict = Depends(require_modulo("pacientes"))):
    res = crear(datos.dict())
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    _auditar(_usuario(payload), "create", f"Paciente {res.get('id_paciente')}")
    return res


@router.put("/{id_paciente}")
def editar_paciente(
    id_paciente: str,
    datos: PacienteActualizar,
    payload: dict = Depends(require_modulo("pacientes")),
):
    res = actualizar(id_paciente, datos.dict(exclude_none=True))
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    _auditar(_usuario(payload), "update", f"Paciente {id_paciente}")
    return res


@router.delete("/{id_paciente}")
def baja_paciente(id_paciente: str, payload: dict = Depends(require_modulo("pacientes"))):
    res = desactivar(id_paciente)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    _auditar(_usuario(payload), "delete", f"Paciente {id_paciente} desactivado")
    return res
