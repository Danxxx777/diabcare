from datetime import datetime, timedelta
from typing import Optional
import jwt
import hashlib
import secrets

SECRETO = "diabcare-secret-2026"
ALGORITMO = "HS256"
EXPIRACION_HORAS = 8

ROLES_VALIDOS = ["administrador", "medico", "analista"]

_codigos_reset = {}

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def iniciar_sesion(email: str, password: str) -> dict:
    from servicios.usuarios.UsuariosServicio import verificar_credenciales
    usuario = verificar_credenciales(email, password)
    if not usuario:
        if email == "admin@diabcare.com" and password == "Admin2026*":
            usuario = {
                "id": "admin-001",
                "nombre": "Administrador",
                "email": email,
                "rol": "administrador"
            }
        else:
            return {"error": "Credenciales incorrectas"}
    payload = {
        "sub": str(usuario["id"]),
        "email": email,
        "rol": usuario["rol"],
        "exp": datetime.utcnow() + timedelta(hours=EXPIRACION_HORAS)
    }
    token = jwt.encode(payload, SECRETO, algorithm=ALGORITMO)
    return {
        "token": token,
        "tipo": "bearer",
        "usuario": {
            "id": str(usuario["id"]),
            "nombre": usuario["nombre"],
            "email": email,
            "rol": usuario["rol"]
        }
    }

def verificar_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRETO, algorithms=[ALGORITMO])
        if payload.get("rol") not in ROLES_VALIDOS:
            return {"error": "Rol del token no reconocido"}
        return {"valido": True, "payload": payload}
    except jwt.ExpiredSignatureError:
        return {"error": "Token expirado"}
    except Exception:
        return {"error": "Token inválido"}

def cambiar_password(token: str, password_actual: str, password_nueva: str) -> dict:
    resultado = verificar_token(token)
    if "error" in resultado:
        return resultado
    email = resultado["payload"]["email"]
    from servicios.usuarios.UsuariosServicio import _extraer, _cargar
    df = _extraer()
    idx = df.index[df["email"] == email].tolist()
    if not idx:
        return {"error": "Usuario no encontrado"}
    if df.at[idx[0], "password_hash"] != _hash(password_actual):
        return {"error": "Contraseña actual incorrecta"}
    df.at[idx[0], "password_hash"] = _hash(password_nueva)
    _cargar(df)
    return {"mensaje": "Contraseña actualizada"}

def generar_codigo_reset(email: str) -> dict:
    from servicios.usuarios.UsuariosServicio import _extraer
    df = _extraer()
    if df.empty or email not in df["email"].values:
        if email != "admin@diabcare.com":
            return {"error": "Email no registrado"}
    codigo = secrets.token_hex(3).upper()
    _codigos_reset[email] = {
        "codigo": codigo,
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    return {"codigo": codigo}

def resetear_password(email: str, codigo: str, password_nueva: str) -> dict:
    if email not in _codigos_reset:
        return {"error": "No hay código de recuperación para este email"}
    datos = _codigos_reset[email]
    if datetime.utcnow() > datos["exp"]:
        return {"error": "Código expirado"}
    if datos["codigo"] != codigo:
        return {"error": "Código incorrecto"}
    del _codigos_reset[email]
    from servicios.usuarios.UsuariosServicio import _extraer, _cargar
    df = _extraer()
    idx = df.index[df["email"] == email].tolist()
    if idx:
        df.at[idx[0], "password_hash"] = _hash(password_nueva)
        _cargar(df)
    return {"mensaje": "Contraseña restablecida"}

def inicializar_admin():
    print("[DiabCare] Roles: administrador | medico | analista")
    print("[DiabCare] Admin: admin@diabcare.com / Admin2026*")