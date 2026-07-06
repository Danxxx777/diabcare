from fastapi import APIRouter, Depends

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.configuracion.ConfiguracionServicio import (
    obtener_configuracion,
    guardar_configuracion,
)
from paquetes.configuracion.ConfiguracionEmailServicio import probar_envio

router = APIRouter(prefix="/api/configuracion", tags=["Configuracion"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


@router.get("/")
def obtener(payload: dict = Depends(require_modulo("configuracion"))):
    return obtener_configuracion()


@router.post("/")
def guardar(datos: dict, payload: dict = Depends(require_modulo("configuracion"))):
    return guardar_configuracion(datos, _usuario(payload))


@router.post("/email/probar")
def probar_email(datos: dict | None = None,
                 payload: dict = Depends(require_modulo("configuracion"))):
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
