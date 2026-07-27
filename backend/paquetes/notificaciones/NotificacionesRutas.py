from fastapi import APIRouter, Depends, Query, HTTPException

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.notificaciones.NotificacionesServicio import (
    listar,
    marcar_leida,
    marcar_todas_leidas,
    estadisticas,
    evaluar_alertas_clinicas,
    crear,
    emitir,
)

router = APIRouter(prefix="/api/notificaciones", tags=["Notificaciones"])


@router.get("/")
def listar_notificaciones(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    solo_no_leidas: bool = False,
    payload: dict = Depends(require_modulo("notificaciones")),
):
    return listar(
        skip=skip,
        limit=limit,
        solo_no_leidas=solo_no_leidas,
        user_id=str(payload.get("sub", "")),
        rol=str(payload.get("rol", "")),
    )


@router.get("/estadisticas")
def stats(payload: dict = Depends(require_modulo("notificaciones"))):
    return estadisticas(
        user_id=str(payload.get("sub", "")),
        rol=str(payload.get("rol", "")),
    )


@router.post("/evaluar")
def evaluar(payload: dict = Depends(require_modulo("notificaciones"))):
    return evaluar_alertas_clinicas()


@router.patch("/{notif_id}/leida")
def leida(notif_id: str, payload: dict = Depends(require_modulo("notificaciones"))):
    resultado = marcar_leida(
        notif_id,
        user_id=str(payload.get("sub", "")),
        rol=str(payload.get("rol", "")),
    )
    if resultado.get("error"):
        raise HTTPException(status_code=404, detail=resultado["error"])
    return resultado


@router.post("/leer-todas")
def leer_todas(payload: dict = Depends(require_modulo("notificaciones"))):
    return marcar_todas_leidas(
        user_id=str(payload.get("sub", "")),
        rol=str(payload.get("rol", "")),
    )


@router.post("/")
def crear_manual(
    datos: dict,
    payload: dict = Depends(require_modulo("notificaciones")),
):
    if payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Solo administrador puede crear notificaciones manuales")
    return emitir(
        datos.get("titulo", "Aviso"),
        datos.get("mensaje", ""),
        datos.get("tipo", "info"),
        destinatario_tipo=datos.get("destinatario_tipo", "todos"),
        destinatario=datos.get("destinatario", ""),
        canal=datos.get("canal") or ("ambos" if datos.get("enviar_email") else "in_app"),
        destino_email=datos.get("destino_email"),
    )
