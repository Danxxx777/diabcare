from fastapi import Header, HTTPException
from paquetes.autenticacion.AutenticacionServicio import verificar_token

ROLES_VALIDOS = ["administrador", "medico", "enfermero", "farmaceutico", "analista"]

MODULOS_POR_CATEGORIA = {
    "Atención clínica": [
        "pacientes", "admisiones", "citas", "mis_citas", "registros", "comorbilidades",
        "laboratorio", "urgencias",
    ],
    "Farmacia y recetas": ["recetas", "farmacia"],
    "Negocio hospitalario": ["facturacion", "rrhh"],
    "Análisis y decisión": ["analisis", "prediccion", "reportes"],
    "Datos e ingeniería": ["dataset", "pipeline_etl", "modelo_ml"],
    "Gobierno y acceso": ["usuarios", "notificaciones", "auditoria", "configuracion"],
}

# administrador = admin de la app: acceso total para supervisión / demos.
# Quienes OPERAN cada área son los roles de negocio (farmacéutico, médico, etc.).
PERMISOS_MODULOS = {
    "usuarios":         ["administrador"],
    "configuracion":    ["administrador"],
    "auditoria":        ["administrador"],
    "pacientes":        ["administrador", "medico", "enfermero", "farmaceutico"],
    "admisiones":       ["administrador", "farmaceutico", "enfermero"],
    "citas":            ["administrador", "farmaceutico", "enfermero"],
    "mis_citas":        ["administrador", "medico"],
    "registros":        ["administrador", "medico"],
    "comorbilidades":   ["administrador", "medico"],
    "analisis":         ["administrador", "medico", "analista", "farmaceutico"],
    "prediccion":       ["administrador", "medico", "analista"],
    "reportes":         ["administrador", "medico", "analista", "farmaceutico"],
    "dataset":          ["administrador", "analista"],
    "pipeline_etl":     ["administrador", "analista"],
    "modelo_ml":        ["administrador", "analista"],
    "notificaciones":   ["administrador", "medico", "analista", "enfermero", "farmaceutico"],
    "facturacion":      ["administrador", "analista", "farmaceutico"],
    "farmacia":         ["administrador", "farmaceutico"],
    "recetas":          ["administrador", "medico"],
    "laboratorio":      ["administrador", "medico", "enfermero"],
    "laboratorio_ordenar": ["administrador", "medico"],
    "laboratorio_resultado": ["administrador", "enfermero"],
    "urgencias":        ["administrador", "medico", "enfermero", "farmaceutico"],
    "urgencias_triage": ["administrador", "enfermero", "farmaceutico"],
    "urgencias_atender": ["administrador", "medico"],
    "rrhh":             ["administrador", "analista"],
}

# Escritura (POST/PUT/DELETE). Lectura sigue en PERMISOS_MODULOS.
# Enfermero: farmacia solo apoyo (ver + dispensar). Analista: facturación/RRHH solo lectura.
PERMISOS_ESCRITURA = {
    "facturacion": ["administrador", "farmaceutico"],
    "rrhh": ["administrador"],
    "farmacia_caja": ["administrador", "farmaceutico"],
}
def _extraer_token(authorization: str, *, permitir_cambio_obligatorio: bool = False) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")
    token = authorization.replace("Bearer ", "").strip()
    resultado = verificar_token(token)
    if "error" in resultado:
        raise HTTPException(status_code=401, detail=resultado["error"])
    payload = resultado["payload"]
    if payload.get("debe_cambiar_password") and not permitir_cambio_obligatorio:
        raise HTTPException(
            status_code=403,
            detail="Debe actualizar su contraseña temporal antes de continuar",
        )
    return payload


def require_auth(authorization: str = Header(None)) -> dict:
    return _extraer_token(authorization)


def require_auth_cambio_password(authorization: str = Header(None)) -> dict:
    """Permite acceso aunque deba_cambiar_password esté activo."""
    return _extraer_token(authorization, permitir_cambio_obligatorio=True)


def require_admin(authorization: str = Header(None)) -> dict:
    payload = _extraer_token(authorization)
    if payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Acceso restringido a administradores")
    return payload


def require_medico(authorization: str = Header(None)) -> dict:
    payload = _extraer_token(authorization)
    if payload.get("rol") not in ["administrador", "medico"]:
        raise HTTPException(status_code=403, detail="Acceso restringido a médicos")
    return payload


def require_analista(authorization: str = Header(None)) -> dict:
    payload = _extraer_token(authorization)
    if payload.get("rol") not in ["administrador", "analista"]:
        raise HTTPException(status_code=403, detail="Acceso restringido a analistas")
    return payload


def require_partner_key(x_api_key: str = Header(None, alias="X-API-Key")) -> dict:
    raise HTTPException(status_code=501, detail="API partner no disponible en demo GA07")


def require_modulo(modulo: str):
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


def require_escritura(clave: str):
    """Mutaciones: usa PERMISOS_ESCRITURA (más restrictivo que la lectura del módulo)."""
    def _check(authorization: str = Header(None)) -> dict:
        payload = _extraer_token(authorization)
        roles = PERMISOS_ESCRITURA.get(clave, ["administrador"])
        if payload.get("rol") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Su rol '{payload.get('rol')}' no puede modificar '{clave}'"
            )
        return payload
    return _check
