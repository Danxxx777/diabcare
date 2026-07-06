from fastapi import Header, HTTPException
from paquetes.autenticacion.AutenticacionServicio import verificar_token

ROLES_VALIDOS = ["administrador", "medico", "analista"]

# Paquetes demo GA07 (P1–P8, P11, P12, P14)
MODULOS_POR_CATEGORIA = {
    "Operaciones clínicas": [
        "pacientes", "admisiones", "citas", "mis_citas", "registros", "analisis", "prediccion", "reportes",
    ],
    "Datos e ingeniería": ["dataset", "pipeline_etl", "modelo_ml"],
    "Seguridad y cumplimiento": ["usuarios", "auditoria", "configuracion", "notificaciones"],
}

PERMISOS_MODULOS = {
    "usuarios":         ["administrador"],
    "configuracion":    ["administrador"],
    "auditoria":        ["administrador"],
    "pacientes":        ["administrador", "medico"],
    "admisiones":       ["administrador"],
    "citas":            ["administrador"],
    "mis_citas":        ["administrador", "medico"],
    "registros":        ["administrador", "medico"],
    "analisis":         ["administrador", "medico", "analista"],
    "prediccion":       ["administrador", "medico", "analista"],
    "reportes":         ["administrador", "medico"],
    "dataset":          ["administrador", "analista"],
    "pipeline_etl":     ["administrador", "analista"],
    "modelo_ml":        ["administrador", "analista"],
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

def require_partner_key(x_api_key: str = Header(None, alias="X-API-Key")) -> dict:
    """Reservado P15 — API partner (iteración futura, ver _futuro/)."""
    raise HTTPException(status_code=501, detail="API partner no disponible en demo GA07")

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
