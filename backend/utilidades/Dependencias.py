from fastapi import Header, HTTPException
from servicios.autenticacion.AutenticacionServicio import verificar_token

ROLES_VALIDOS = ["administrador", "medico", "analista"]

PERMISOS_MODULOS = {
    "usuarios":         ["administrador"],
    "configuracion":    ["administrador"],
    "auditoria":        ["administrador"],
    "benchmarking":     ["administrador"],
    "registros":        ["administrador", "medico"],
    "analisis":         ["administrador", "medico", "analista"],
    "prediccion":       ["administrador", "medico"],
    "reportes":         ["administrador", "medico"],
    "dataset":          ["administrador", "analista"],
    "pipeline_etl":     ["administrador", "analista"],
    "modelo_ml":        ["administrador", "analista"],
    "integraciones":    ["administrador", "analista"],
    "notificaciones":   ["administrador", "medico", "analista"],
}

def _extraer_token(authorization: str) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")
    token = authorization.replace("Bearer ", "").strip()
    resultado = verificar_token(token)
    if "error" in resultado:
        raise HTTPException(status_code=401, detail=resultado["error"])
    return resultado["payload"]

def require_auth(authorization: str = Header(None)) -> dict:
    """Verifica que el token sea válido. Retorna el payload JWT."""
    return _extraer_token(authorization)

def require_admin(authorization: str = Header(None)) -> dict:
    """Solo administrador."""
    payload = _extraer_token(authorization)
    if payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Acceso restringido a administradores")
    return payload

def require_medico(authorization: str = Header(None)) -> dict:
    """Administrador o médico."""
    payload = _extraer_token(authorization)
    if payload.get("rol") not in ["administrador", "medico"]:
        raise HTTPException(status_code=403, detail="Acceso restringido a médicos")
    return payload

def require_analista(authorization: str = Header(None)) -> dict:
    """Administrador o analista."""
    payload = _extraer_token(authorization)
    if payload.get("rol") not in ["administrador", "analista"]:
        raise HTTPException(status_code=403, detail="Acceso restringido a analistas")
    return payload

def require_modulo(modulo: str):
    """
    Dependencia dinámica por módulo.
    Uso: Depends(require_modulo('dataset'))
    """
    def _check(authorization: str = Header(None)) -> dict:
        payload = _extraer_token(authorization)
        roles_permitidos = PERMISOS_MODULOS.get(modulo, ["administrador"])
        if payload.get("rol") not in roles_permitidos:
            raise HTTPException(
                status_code=403,
                detail=f"Su rol '{payload.get('rol')}' no tiene acceso al módulo '{modulo}'"
            )
        return payload
    return _check
