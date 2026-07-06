from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from paquetes.autenticacion.AutenticacionServicio import (
    iniciar_sesion, verificar_token, cambiar_password,
    generar_codigo_reset, resetear_password, obtener_perfil, actualizar_perfil,
)

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

class LoginEntrada(BaseModel):
    email: str
    password: str

class CambiarPasswordEntrada(BaseModel):
    password_actual: str
    password_nueva: str

class PerfilEntrada(BaseModel):
    nombre: str

class RecuperarEntrada(BaseModel):
    email: str

class ResetearEntrada(BaseModel):
    email: str
    codigo: str
    password_nueva: str

class RegistroEntrada(BaseModel):
    nombre: str
    email: str
    password: str
    rol_solicitado: str = "analista"
    motivo: Optional[str] = None

@router.post("/login")
def login(datos: LoginEntrada):
    resultado = iniciar_sesion(datos.email, datos.password)
    if "error" in resultado:
        raise HTTPException(status_code=401, detail=resultado["error"])
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(datos.email, "login", "autenticacion", "Inicio de sesión exitoso")
    except Exception:
        pass
    return resultado

@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    return {"mensaje": "Sesión cerrada correctamente"}

@router.post("/recuperar")
def recuperar(datos: RecuperarEntrada):
    resultado = generar_codigo_reset(datos.email)
    if "error" in resultado:
        raise HTTPException(status_code=404, detail=resultado["error"])
    resp = {"mensaje": f"Código enviado al email {datos.email}"}
    if not resultado.get("email_enviado"):
        resp["codigo_dev"] = resultado.get("codigo")
    return resp

@router.post("/resetear")
def resetear(datos: ResetearEntrada):
    resultado = resetear_password(datos.email, datos.codigo, datos.password_nueva)
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    return {"mensaje": "Contraseña actualizada correctamente"}

@router.post("/registro")
@router.post("/solicitud-acceso")
def solicitud_acceso(datos: RegistroEntrada):
    from paquetes.autenticacion.SolicitudesAccesoServicio import crear_solicitud
    resultado = crear_solicitud(
        datos.nombre.strip(),
        datos.email.strip().lower(),
        datos.password,
        datos.rol_solicitado,
        datos.motivo or "",
    )
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    return resultado

@router.get("/perfil")
def perfil(authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else ""
    resultado = obtener_perfil(token)
    if "error" in resultado:
        raise HTTPException(status_code=401, detail=resultado["error"])
    return resultado


@router.put("/perfil")
def actualizar(datos: PerfilEntrada, authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else ""
    resultado = actualizar_perfil(token, datos.nombre)
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    return resultado


@router.put("/cambiar-password")
def cambiar(datos: CambiarPasswordEntrada, authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else ""
    resultado = cambiar_password(token, datos.password_actual, datos.password_nueva)
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    return {"mensaje": "Contraseña cambiada correctamente"}

@router.get("/verificar")
def verificar(authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else ""
    resultado = verificar_token(token)
    if "error" in resultado:
        raise HTTPException(status_code=401, detail=resultado["error"])
    return resultado