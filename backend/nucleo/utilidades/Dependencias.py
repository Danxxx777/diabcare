from typing import Optional

from fastapi import Header, HTTPException, Request

from paquetes.autenticacion.AuthCookies import COOKIE_SESION
from paquetes.autenticacion.AutenticacionServicio import verificar_token

ROLES_VALIDOS = ["administrador", "medico", "enfermero", "farmaceutico", "analista"]

MODULOS_POR_CATEGORIA = {
    "Atención clínica": [
        "pacientes", "admisiones", "citas", "mis_citas", "registros", "comorbilidades",
        "laboratorio", "urgencias", "instrumental",
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
    "admisiones":       ["administrador", "enfermero"],
    "habitaciones":     ["administrador", "medico", "enfermero"],
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
    "urgencias_triage": ["administrador", "enfermero"],
    "urgencias_atender": ["administrador", "medico"],
    "rrhh":             ["administrador", "analista"],
    "instrumental":     ["administrador", "enfermero"],
}

# Escritura (POST/PUT/DELETE). Lectura sigue en PERMISOS_MODULOS.
# Enfermero: farmacia solo apoyo (ver + dispensar). Analista: facturación/RRHH solo lectura.
PERMISOS_ESCRITURA = {
    "facturacion": ["administrador", "farmaceutico"],
    "rrhh": ["administrador"],
    "farmacia_caja": ["administrador", "farmaceutico"],
    "habitaciones": ["administrador", "enfermero"],
}

_MARCAS_INVALIDAS = frozenset({"", "null", "undefined", "sesion", "cookie", "none"})


def _limpiar_token(valor: Optional[str]) -> str:
    t = (valor or "").replace("Bearer ", "").strip()
    if t.lower() in _MARCAS_INVALIDAS:
        return ""
    return t


def resolver_token_crudo(
    request: Optional[Request] = None,
    authorization: Optional[str] = None,
    token_query: Optional[str] = None,
) -> str:
    """Prioridad: Authorization Bearer real → ?token= → cookie httpOnly."""
    t = _limpiar_token(authorization)
    if t:
        return t
    t = _limpiar_token(token_query)
    if t:
        return t
    if request is not None:
        t = _limpiar_token(request.cookies.get(COOKIE_SESION))
        if t:
            return t
    return ""


def _extraer_token(
    authorization_or_token: str,
    *,
    permitir_cambio_obligatorio: bool = False,
) -> dict:
    """Valida un JWT ya resuelto (string crudo o 'Bearer …')."""
    token = _limpiar_token(authorization_or_token)
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido")
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


def auth_desde_request(
    request: Request,
    authorization: Optional[str] = None,
    *,
    permitir_cambio_obligatorio: bool = False,
    token_query: Optional[str] = None,
) -> dict:
    token = resolver_token_crudo(request, authorization, token_query)
    return _extraer_token(token, permitir_cambio_obligatorio=permitir_cambio_obligatorio)


def require_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict:
    return auth_desde_request(request, authorization)


def require_auth_cambio_password(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict:
    """Permite acceso aunque deba_cambiar_password esté activo."""
    return auth_desde_request(request, authorization, permitir_cambio_obligatorio=True)


def require_admin(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict:
    payload = auth_desde_request(request, authorization)
    if payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Acceso restringido a administradores")
    return payload


def require_medico(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict:
    payload = auth_desde_request(request, authorization)
    if payload.get("rol") not in ["administrador", "medico"]:
        raise HTTPException(status_code=403, detail="Acceso restringido a médicos")
    return payload


def require_analista(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict:
    payload = auth_desde_request(request, authorization)
    if payload.get("rol") not in ["administrador", "analista"]:
        raise HTTPException(status_code=403, detail="Acceso restringido a analistas")
    return payload


def require_partner_key(x_api_key: str = Header(None, alias="X-API-Key")) -> dict:
    raise HTTPException(status_code=501, detail="API partner no disponible en demo GA07")


def require_modulo(modulo: str):
    def _check(
        request: Request,
        authorization: Optional[str] = Header(None),
    ) -> dict:
        payload = auth_desde_request(request, authorization)
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
    def _check(
        request: Request,
        authorization: Optional[str] = Header(None),
    ) -> dict:
        payload = auth_desde_request(request, authorization)
        roles = PERMISOS_ESCRITURA.get(clave, ["administrador"])
        if payload.get("rol") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Su rol '{payload.get('rol')}' no puede modificar '{clave}'"
            )
        return payload
    return _check
