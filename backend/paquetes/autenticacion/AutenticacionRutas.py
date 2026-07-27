from fastapi import APIRouter, Header, HTTPException, Request, Depends, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from paquetes.autenticacion.AutenticacionServicio import (
    iniciar_sesion, verificar_token, cambiar_password,
    generar_codigo_reset, resetear_password, obtener_perfil, actualizar_perfil,
    cerrar_sesion,
)
from nucleo.utilidades.Dependencias import require_admin, require_auth_cambio_password

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


class LoginEntrada(BaseModel):
    email: str
    password: str


class CambiarPasswordEntrada(BaseModel):
    password_actual: str
    password_nueva: str


class PerfilEntrada(BaseModel):
    nombre: str
    telefono: Optional[str] = None
    cargo: Optional[str] = None
    bio: Optional[str] = None
    idioma: Optional[str] = "es"
    notif_email: Optional[bool] = True


class RecuperarEntrada(BaseModel):
    email: str


class ResetearEntrada(BaseModel):
    email: str
    codigo: str
    password_nueva: str


class RegistroEntrada(BaseModel):
    nombre: str
    email: str
    password: Optional[str] = None
    rol_solicitado: str = "analista"
    motivo: Optional[str] = None


def _meta_request(request: Request) -> tuple[str, str]:
    ip = (request.client.host if request.client else "") or ""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        ip = fwd.split(",")[0].strip()
    ua = request.headers.get("user-agent", "")[:250]
    return ip, ua


@router.post("/login")
def login(datos: LoginEntrada, request: Request):
    ip, ua = _meta_request(request)
    resultado = iniciar_sesion(datos.email, datos.password, ip=ip, user_agent=ua)
    if "error" in resultado:
        try:
            from paquetes.auditoria.AuditoriaServicio import registrar
            registrar(
                datos.email, "login", "autenticacion", "Intento fallido",
                ip=ip, user_agent=ua, resultado="fallo",
            )
        except Exception:
            pass
        raise HTTPException(status_code=401, detail=resultado["error"])
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        jti = ""
        # jti no viene en respuesta usuario; reconstruir de token si hace falta
        tok = resultado.get("token", "")
        if tok:
            vr = verificar_token(tok, validar_sesion=False)
            jti = str(vr.get("payload", {}).get("jti") or "")
        registrar(
            datos.email, "login", "autenticacion", "Inicio de sesión exitoso",
            ip=ip, user_agent=ua, sesion_id=jti, resultado="ok",
        )
    except Exception:
        pass
    return resultado


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None), request: Request = None):
    token = authorization.replace("Bearer ", "") if authorization else ""
    resultado = cerrar_sesion(token)
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        ip, ua = _meta_request(request) if request else ("", "")
        email = ""
        if token:
            vr = verificar_token(token, validar_sesion=False)
            email = str(vr.get("payload", {}).get("email") or "")
        registrar(email or "anon", "logout", "autenticacion", "Cierre de sesión", ip=ip, user_agent=ua)
    except Exception:
        pass
    return resultado


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
        datos.rol_solicitado,
        datos.motivo or "",
        datos.password,
    )
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    return resultado


@router.get("/perfil")
def perfil(payload: dict = Depends(require_auth_cambio_password)):
    from paquetes.usuarios.UsuariosServicio import obtener_usuario, asegurar_admin, ADMIN_ID
    uid = str(payload.get("sub", ""))
    email = str(payload.get("email") or "")
    u = obtener_usuario(uid)
    if u.get("error") and email == "admin@diabcare.com":
        asegurar_admin()
        u = obtener_usuario(ADMIN_ID)
    if "error" not in u:
        return u
    raise HTTPException(status_code=401, detail="Usuario no encontrado")


@router.put("/perfil")
def actualizar(datos: PerfilEntrada, authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else ""
    resultado = actualizar_perfil(token, datos.dict())
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    return resultado


@router.get("/perfil/foto")
def foto_perfil(payload: dict = Depends(require_auth_cambio_password)):
    from paquetes.clinico.pacientes.FotosEntidadServicio import leer_bytes_foto
    from paquetes.usuarios.UsuariosServicio import ADMIN_ID
    uid = str(payload.get("sub", "")) or ADMIN_ID
    if str(payload.get("email") or "") == "admin@diabcare.com":
        uid = ADMIN_ID
    res = leer_bytes_foto("usuario", uid)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res["error"])
    return Response(content=res["contenido"], media_type=res.get("mime_type") or "image/jpeg")


@router.post("/perfil/foto")
async def subir_foto_perfil(
    archivo: UploadFile = File(...),
    payload: dict = Depends(require_auth_cambio_password),
):
    from paquetes.clinico.pacientes.FotosEntidadServicio import guardar_foto
    from paquetes.usuarios.UsuariosServicio import asegurar_admin, ADMIN_ID, obtener_usuario
    uid = str(payload.get("sub", ""))
    email = str(payload.get("email") or "")
    if email == "admin@diabcare.com" or uid in ("", "admin-001", ADMIN_ID):
        asegurar_admin()
        uid = ADMIN_ID
    if not uid:
        raise HTTPException(status_code=401, detail="Usuario no válido")
    # Si aún no está en store (otro usuario), exige existir
    if obtener_usuario(uid).get("error"):
        raise HTTPException(status_code=400, detail="Usuario no encontrado en el sistema; no se puede guardar la foto")
    contenido = await archivo.read()
    if not contenido:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    res = guardar_foto(
        "usuario",
        uid,
        contenido,
        archivo.content_type or "image/jpeg",
        email or str(payload.get("nombre") or "usuario"),
    )
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res["error"])
    res["tiene_foto"] = True
    res["id_usuario"] = uid
    return res


@router.put("/cambiar-password")
def cambiar(datos: CambiarPasswordEntrada, authorization: Optional[str] = Header(None), request: Request = None):
    token = authorization.replace("Bearer ", "") if authorization else ""
    resultado = cambiar_password(token, datos.password_actual, datos.password_nueva)
    if "error" in resultado:
        raise HTTPException(status_code=400, detail=resultado["error"])
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        ip, ua = _meta_request(request) if request else ("", "")
        vr = verificar_token(token, validar_sesion=False)
        email = str(vr.get("payload", {}).get("email") or "")
        registrar(email, "update", "autenticacion", "Cambio de contraseña", ip=ip, user_agent=ua)
    except Exception:
        pass
    return resultado


@router.get("/verificar")
def verificar(authorization: Optional[str] = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else ""
    resultado = verificar_token(token)
    if "error" in resultado:
        raise HTTPException(status_code=401, detail=resultado["error"])
    return resultado


@router.get("/mis-sesiones")
def mis_sesiones(payload: dict = Depends(require_auth_cambio_password)):
    from paquetes.autenticacion.SesionesServicio import listar_usuario
    return {
        "sesiones": listar_usuario(
            str(payload.get("sub", "")),
            email=str(payload.get("email") or ""),
        ),
        "jti_actual": str(payload.get("jti") or ""),
    }


@router.delete("/mis-sesiones/{id_sesion}")
def revocar_mi_sesion(id_sesion: str, payload: dict = Depends(require_auth_cambio_password)):
    """Revoca otra sesión propia. No permite cerrar la sesión actual (otro admin sí puede)."""
    from paquetes.autenticacion.SesionesServicio import pertenece_a_usuario, revocar
    uid = str(payload.get("sub", ""))
    email = str(payload.get("email") or "")
    jti_actual = str(payload.get("jti") or "")
    if jti_actual and str(id_sesion) == jti_actual:
        raise HTTPException(
            status_code=400,
            detail="No puedes cerrar tu propia sesión activa. Pide a otro administrador que la revoque, o usa Cerrar sesión al salir.",
        )
    if not pertenece_a_usuario(id_sesion, uid, email=email):
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    r = revocar(id_sesion)
    if r.get("error"):
        raise HTTPException(status_code=404, detail=r["error"])
    return {**r, "era_actual": False}


@router.post("/mis-sesiones/cerrar-todas")
def cerrar_todas_mis_sesiones(
    payload: dict = Depends(require_auth_cambio_password),
):
    """Cierra el resto de sesiones del usuario; la actual siempre se conserva."""
    from paquetes.autenticacion.SesionesServicio import revocar_todas_usuario
    uid = str(payload.get("sub", ""))
    email = str(payload.get("email") or "")
    jti = str(payload.get("jti") or "") or None
    if not jti:
        raise HTTPException(status_code=400, detail="Sesión actual no identificada")
    n = revocar_todas_usuario(uid, excepto=jti, email=email)
    return {
        "mensaje": f"{n} sesión(es) cerrada(s). Tu sesión actual sigue activa.",
        "cerradas": n,
        "incluye_actual": False,
    }


@router.get("/sesiones")
def listar_sesiones_admin(
    skip: int = 0,
    limit: int = 50,
    solo_activas: bool = True,
    payload: dict = Depends(require_admin),
):
    from paquetes.autenticacion.SesionesServicio import listar_todas
    return listar_todas(skip=skip, limit=limit, solo_activas=solo_activas)


@router.delete("/sesiones/{id_sesion}")
def revocar_sesion_admin(id_sesion: str, payload: dict = Depends(require_admin)):
    from paquetes.autenticacion.SesionesServicio import revocar
    r = revocar(id_sesion)
    if r.get("error"):
        raise HTTPException(status_code=404, detail=r["error"])
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(payload.get("email", "admin"), "revoke", "autenticacion", f"Sesión revocada: {id_sesion}")
    except Exception:
        pass
    return r
