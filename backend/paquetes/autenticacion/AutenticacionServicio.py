from datetime import datetime, timedelta
from typing import Optional
import jwt
import secrets
import string

from nucleo.utilidades.PasswordHash import hash_password, verificar_password, necesita_rehash
from paquetes.configuracion.ConfiguracionAjustes import (
    JWT_SECRET,
    JWT_ALGORITMO,
    JWT_EXPIRACION_HORAS,
)

SECRETO = JWT_SECRET
ALGORITMO = JWT_ALGORITMO
EXPIRACION_HORAS = JWT_EXPIRACION_HORAS

ROLES_VALIDOS = ["administrador", "medico", "enfermero", "farmaceutico", "analista"]

_codigos_reset = {}


def _hash(password: str) -> str:
    """API interna: bcrypt (antes era SHA-256)."""
    return hash_password(password)


def generar_password_temporal(longitud: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(longitud))


def _debe_cambiar(usuario: dict) -> bool:
    v = usuario.get("debe_cambiar_password")
    if v is True:
        return True
    if isinstance(v, str) and v.strip().lower() in ("true", "1", "yes", "si", "sí"):
        return True
    return False


def iniciar_sesion(
    email: str,
    password: str,
    ip: str = "",
    user_agent: str = "",
) -> dict:
    from paquetes.usuarios.UsuariosServicio import verificar_credenciales
    from paquetes.autenticacion.SesionesServicio import crear_sesion

    usuario = verificar_credenciales(email, password)
    if not usuario:
        from paquetes.configuracion.ConfiguracionAjustes import ALLOW_BOOTSTRAP_ADMIN
        if (
            ALLOW_BOOTSTRAP_ADMIN
            and email == "admin@diabcare.com"
            and password == "Admin2026*"
        ):
            from paquetes.usuarios.UsuariosServicio import asegurar_admin
            asegurar_admin(password)
            usuario = verificar_credenciales(email, password)
        if not usuario:
            return {"error": "Credenciales incorrectas"}

    debe = _debe_cambiar(usuario)
    jti = crear_sesion(
        str(usuario["id"]),
        email,
        horas=EXPIRACION_HORAS,
        ip=ip,
        user_agent=user_agent,
    )
    payload = {
        "sub": str(usuario["id"]),
        "email": email,
        "nombre": str(usuario.get("nombre") or ""),
        "rol": usuario["rol"],
        "jti": jti,
        "debe_cambiar_password": debe,
        "exp": datetime.utcnow() + timedelta(hours=EXPIRACION_HORAS),
    }
    token = jwt.encode(payload, SECRETO, algorithm=ALGORITMO)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    tiene_foto = False
    try:
        from paquetes.clinico.pacientes.FotosEntidadServicio import obtener_principal
        tiene_foto = bool(obtener_principal("usuario", str(usuario["id"])))
    except Exception:
        pass
    return {
        "token": token,
        "tipo": "bearer",
        "expira_en": EXPIRACION_HORAS * 3600,
        "usuario": {
            "id": str(usuario["id"]),
            "nombre": usuario["nombre"],
            "email": email,
            "rol": usuario["rol"],
            "debe_cambiar_password": debe,
            "tiene_foto": tiene_foto,
        },
    }


def verificar_token(token: str, *, validar_sesion: bool = True) -> dict:
    try:
        payload = jwt.decode(token, SECRETO, algorithms=[ALGORITMO])
        if payload.get("rol") not in ROLES_VALIDOS:
            return {"error": "Rol del token no reconocido"}
        jti = payload.get("jti")
        if validar_sesion and jti:
            from paquetes.autenticacion.SesionesServicio import sesion_valida
            if not sesion_valida(str(jti)):
                return {"error": "Sesión revocada o expirada"}
        return {"valido": True, "payload": payload}
    except jwt.ExpiredSignatureError:
        return {"error": "Token expirado"}
    except Exception:
        return {"error": "Token inválido"}


def cerrar_sesion(token: str) -> dict:
    resultado = verificar_token(token, validar_sesion=False)
    if "error" in resultado:
        return {"mensaje": "Sesión cerrada"}
    jti = resultado["payload"].get("jti")
    if jti:
        from paquetes.autenticacion.SesionesServicio import revocar
        revocar(str(jti))
    return {"mensaje": "Sesión cerrada correctamente"}


def cambiar_password(token: str, password_actual: str, password_nueva: str) -> dict:
    resultado = verificar_token(token)
    if "error" in resultado:
        return resultado
    if len(password_nueva or "") < 8:
        return {"error": "La nueva contraseña debe tener al menos 8 caracteres"}
    email = resultado["payload"]["email"]
    from paquetes.usuarios.UsuariosServicio import _extraer, _cargar, _valor_escritura
    df = _extraer()
    idx = df.index[df["email"] == email].tolist()
    if not idx:
        return {"error": "Usuario no encontrado"}
    stored = str(df.at[idx[0], "password_hash"] or "")
    if not verificar_password(password_actual, stored):
        return {"error": "Contraseña actual incorrecta"}
    df.at[idx[0], "password_hash"] = hash_password(password_nueva)
    df.at[idx[0], "debe_cambiar_password"] = _valor_escritura("debe_cambiar_password", False)
    _cargar(df)
    from paquetes.autenticacion.SesionesServicio import crear_sesion, revocar
    old_jti = resultado["payload"].get("jti")
    if old_jti:
        revocar(str(old_jti))
    uid = str(resultado["payload"].get("sub"))
    jti = crear_sesion(uid, email, horas=EXPIRACION_HORAS)
    payload = {
        "sub": uid,
        "email": email,
        "nombre": str(resultado["payload"].get("nombre") or ""),
        "rol": resultado["payload"].get("rol"),
        "jti": jti,
        "debe_cambiar_password": False,
        "exp": datetime.utcnow() + timedelta(hours=EXPIRACION_HORAS),
    }
    token_nuevo = jwt.encode(payload, SECRETO, algorithm=ALGORITMO)
    if isinstance(token_nuevo, bytes):
        token_nuevo = token_nuevo.decode("utf-8")
    return {
        "mensaje": "Contraseña actualizada",
        "token": token_nuevo,
        "expira_en": EXPIRACION_HORAS * 3600,
        "usuario": {
            "id": uid,
            "nombre": payload["nombre"],
            "email": email,
            "rol": payload["rol"],
            "debe_cambiar_password": False,
        },
    }


def generar_codigo_reset(email: str) -> dict:
    from paquetes.usuarios.UsuariosServicio import _extraer
    df = _extraer()
    if df.empty or email not in df["email"].values:
        if email != "admin@diabcare.com":
            return {"error": "Email no registrado"}
    codigo = secrets.token_hex(3).upper()
    _codigos_reset[email] = {
        "codigo": codigo,
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    email_enviado = False
    try:
        from paquetes.configuracion.ConfiguracionServicio import obtener_configuracion
        from paquetes.configuracion.ConfiguracionEmailPlantillas import (
            asunto_plantilla,
            render_plantilla,
        )
        from paquetes.configuracion.ConfiguracionEmailServicio import enviar_correo

        cfg = obtener_configuracion(enmascarar_secretos=False)
        if cfg.get("email"):
            texto, html = render_plantilla("recuperacion", codigo=codigo)
            r = enviar_correo(email, asunto_plantilla("recuperacion"), texto, html, plantilla="recuperacion")
            email_enviado = "error" not in r
    except Exception:
        pass
    return {"codigo": codigo, "email_enviado": email_enviado}


def resetear_password(email: str, codigo: str, password_nueva: str) -> dict:
    if email not in _codigos_reset:
        return {"error": "No hay código de recuperación para este email"}
    datos = _codigos_reset[email]
    if datetime.utcnow() > datos["exp"]:
        return {"error": "Código expirado"}
    if datos["codigo"] != codigo:
        return {"error": "Código incorrecto"}
    if len(password_nueva or "") < 8:
        return {"error": "La nueva contraseña debe tener al menos 8 caracteres"}
    del _codigos_reset[email]
    from paquetes.usuarios.UsuariosServicio import _extraer, _cargar, _valor_escritura
    df = _extraer()
    idx = df.index[df["email"] == email].tolist()
    if idx:
        df.at[idx[0], "password_hash"] = hash_password(password_nueva)
        df.at[idx[0], "debe_cambiar_password"] = _valor_escritura("debe_cambiar_password", False)
        _cargar(df)
    return {"mensaje": "Contraseña restablecida"}


def actualizar_perfil(token: str, datos: dict) -> dict:
    resultado = verificar_token(token)
    if "error" in resultado:
        return resultado
    payload = resultado["payload"]
    uid = str(payload.get("sub", ""))
    email = str(payload.get("email") or "")
    from paquetes.usuarios.UsuariosServicio import (
        actualizar_perfil_campos,
        obtener_usuario,
        asegurar_admin,
        ADMIN_ID,
    )
    u = obtener_usuario(uid)
    if u.get("error") and email == "admin@diabcare.com":
        asegurar_admin(datos=datos)
        uid = ADMIN_ID
        u = obtener_usuario(uid)
    if u.get("error"):
        return {"error": "Usuario no encontrado"}
    return actualizar_perfil_campos(uid, datos or {})


def obtener_perfil(token: str) -> dict:
    resultado = verificar_token(token)
    if "error" in resultado:
        return resultado
    payload = resultado["payload"]
    uid = str(payload.get("sub", ""))
    email = str(payload.get("email") or "")
    from paquetes.usuarios.UsuariosServicio import obtener_usuario, asegurar_admin, ADMIN_ID
    u = obtener_usuario(uid)
    if u.get("error") and email == "admin@diabcare.com":
        asegurar_admin()
        u = obtener_usuario(ADMIN_ID)
    if "error" not in u:
        return u
    return {"error": "Usuario no encontrado"}


def inicializar_admin():
    pass
