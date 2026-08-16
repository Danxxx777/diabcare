from fastapi import APIRouter, Depends, Body

from nucleo.utilidades.Dependencias import require_modulo
from nucleo.utilidades.UrlPublica import alcance_url
from paquetes.configuracion.ConfiguracionServicio import (
    obtener_configuracion,
    guardar_configuracion,
)
from paquetes.configuracion.ConfiguracionEmailServicio import (
    probar_envio,
    estado_correo,
    aplicar_preset_mailpit,
    aplicar_preset_gmail,
)

router = APIRouter(prefix="/api/configuracion", tags=["Configuracion"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("email") or payload.get("sub")
            or payload.get("nombre") or "sistema")


@router.get("/")
def obtener(payload: dict = Depends(require_modulo("configuracion"))):
    cfg = obtener_configuracion()
    cfg["alcance_qr"] = alcance_url()
    return cfg


@router.post("/")
def guardar(datos: dict, payload: dict = Depends(require_modulo("configuracion"))):
    r = guardar_configuracion(datos, _usuario(payload))
    cfg = r.get("configuracion") if isinstance(r, dict) else None
    if isinstance(cfg, dict):
        cfg["alcance_qr"] = alcance_url()
        r["configuracion"] = cfg
    return r


@router.get("/email/estado")
def email_estado(payload: dict = Depends(require_modulo("configuracion"))):
    return estado_correo()


@router.post("/email/preset/mailpit")
def email_preset_mailpit(payload: dict = Depends(require_modulo("configuracion"))):
    return aplicar_preset_mailpit(_usuario(payload))


@router.post("/email/preset/gmail")
def email_preset_gmail(
    datos: dict = Body(default={}),
    payload: dict = Depends(require_modulo("configuracion")),
):
    gmail = (datos or {}).get("gmail") or (datos or {}).get("email") or ""
    return aplicar_preset_gmail(_usuario(payload), gmail)


@router.post("/email/probar")
def probar_email(
    datos: dict = Body(default={}),
    payload: dict = Depends(require_modulo("configuracion")),
):
    destino = (datos or {}).get("destino")
    resultado = probar_envio(destino)
    if resultado.get("error"):
        return resultado
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(_usuario(payload), "test", "configuracion",
                  f"Prueba de correo enviada a {destino or 'destino configurado'}")
    except Exception:
        pass
    return resultado
