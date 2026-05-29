from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from servicios.usuarios.UsuariosServicio import (
    crear_usuario, obtener_usuarios, obtener_usuario,
    editar_usuario, desactivar_usuario, asignar_rol
)
from utilidades.Dependencias import require_admin, ROLES_VALIDOS

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])

class CrearUsuarioEntrada(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str = "medico"

class EditarUsuarioEntrada(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    rol: Optional[str] = None

class AsignarRolEntrada(BaseModel):
    rol: str

@router.get("/")
def listar(payload: dict = Depends(require_admin)):
    return obtener_usuarios()

@router.get("/roles")
def listar_roles(payload: dict = Depends(require_admin)):
    return {"roles": ROLES_VALIDOS}

@router.get("/{id_usuario}")
def obtener(id_usuario: str, payload: dict = Depends(require_admin)):
    resultado = obtener_usuario(id_usuario)
    if "error" in resultado:
        raise HTTPException(status_code=404, detail=resultado["error"])
    return resultado

@router.post("/")
def crear(datos: CrearUsuarioEntrada, payload: dict = Depends(require_admin)):
    if datos.rol not in ROLES_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Roles válidos: {ROLES_VALIDOS}"
        )
    resultado = crear_usuario(datos.nombre, datos.email, datos.password, datos.rol)
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    return resultado

@router.put("/{id_usuario}")
def editar(id_usuario: str, datos: EditarUsuarioEntrada, payload: dict = Depends(require_admin)):
    cambios = datos.dict(exclude_none=True)
    if "rol" in cambios and cambios["rol"] not in ROLES_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Roles válidos: {ROLES_VALIDOS}"
        )
    resultado = editar_usuario(id_usuario, cambios)
    if "error" in resultado:
        raise HTTPException(status_code=404, detail=resultado["error"])
    return resultado

@router.delete("/{id_usuario}")
def desactivar(id_usuario: str, payload: dict = Depends(require_admin)):
    # Evitar que el admin se desactive a sí mismo
    if id_usuario == payload.get("sub"):
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta")
    resultado = desactivar_usuario(id_usuario)
    if "error" in resultado:
        raise HTTPException(status_code=404, detail=resultado["error"])
    return resultado

@router.put("/{id_usuario}/rol")
def cambiar_rol(id_usuario: str, datos: AsignarRolEntrada, payload: dict = Depends(require_admin)):
    if datos.rol not in ROLES_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Roles válidos: {ROLES_VALIDOS}"
        )
    if id_usuario == payload.get("sub"):
        raise HTTPException(status_code=400, detail="No puedes cambiar tu propio rol")
    resultado = asignar_rol(id_usuario, datos.rol)
    if "error" in resultado:
        raise HTTPException(status_code=404, detail=resultado["error"])
    return resultado
