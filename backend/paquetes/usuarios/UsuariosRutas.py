from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from paquetes.usuarios.UsuariosServicio import (
    crear_usuario, obtener_usuarios, obtener_usuario,
    editar_usuario, desactivar_usuario, asignar_rol
)
from nucleo.utilidades.Dependencias import require_admin, require_modulo, ROLES_VALIDOS

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

class AprobarSolicitudEntrada(BaseModel):
    rol: Optional[str] = None

@router.get("/solicitudes")
def listar_solicitudes(estado: Optional[str] = "pendiente", payload: dict = Depends(require_admin)):
    from paquetes.autenticacion.SolicitudesAccesoServicio import listar_solicitudes as listar
    return listar(estado)

@router.post("/solicitudes/{id_solicitud}/aprobar")
def aprobar_solicitud(
    id_solicitud: str,
    datos: AprobarSolicitudEntrada,
    payload: dict = Depends(require_admin),
):
    if datos.rol and datos.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Roles válidos: {ROLES_VALIDOS}")
    from paquetes.autenticacion.SolicitudesAccesoServicio import aprobar_solicitud as aprobar
    resultado = aprobar(id_solicitud, datos.rol, payload.get("email", "admin"))
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    return resultado

@router.post("/solicitudes/{id_solicitud}/rechazar")
def rechazar_solicitud(id_solicitud: str, payload: dict = Depends(require_admin)):
    from paquetes.autenticacion.SolicitudesAccesoServicio import rechazar_solicitud as rechazar
    resultado = rechazar(id_solicitud, payload.get("email", "admin"))
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    return resultado

@router.get("/")
def listar(payload: dict = Depends(require_admin)):
    return obtener_usuarios()

@router.get("/roles")
def listar_roles(payload: dict = Depends(require_admin)):
    return {"roles": ROLES_VALIDOS}

@router.get("/medicos")
def catalogo_medicos(payload: dict = Depends(require_modulo("citas"))):
    """Catálogo para recepción (admin / farmacia / enfermería) al separar turnos."""
    from paquetes.usuarios.UsuariosServicio import listar_activos_por_rol
    return {"medicos": listar_activos_por_rol("medico")}

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
