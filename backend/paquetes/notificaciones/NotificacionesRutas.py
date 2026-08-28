from fastapi import APIRouter, Depends, Query, HTTPException

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.notificaciones.NotificacionesServicio import (
    listar,
    marcar_leida,
    marcar_todas_leidas,
    purgar_leidas,
    estadisticas,
    evaluar_alertas_clinicas,
    emitir,
    emitir_a_roles,
    etiqueta_rol,
    ROLES_VALIDOS,
)

router = APIRouter(prefix="/api/notificaciones", tags=["Notificaciones"])


@router.get("/")
def listar_notificaciones(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    solo_no_leidas: bool = False,
    incluir_registros: bool = False,
    payload: dict = Depends(require_modulo("notificaciones")),
):
    """Bandeja del rol. Por defecto solo lo accionable; incluir_registros suma
    el rastro de acciones propias (reportes, reentrenamientos, generaciones)."""
    return listar(
        skip=skip,
        limit=limit,
        solo_no_leidas=solo_no_leidas,
        incluir_registros=incluir_registros,
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


@router.delete("/leidas")
def borrar_leidas(dias: int = 0, payload: dict = Depends(require_modulo("notificaciones"))):
    """Vacía las notificaciones ya leídas (opcionalmente conserva las de N días)."""
    return purgar_leidas(
        user_id=payload.get("sub") or "",
        rol=payload.get("rol") or "",
        dias=dias,
    )


@router.post("/leer-todas")
def leer_todas(payload: dict = Depends(require_modulo("notificaciones"))):
    return marcar_todas_leidas(
        user_id=str(payload.get("sub", "")),
        rol=str(payload.get("rol", "")),
    )


@router.get("/roles")
def roles_destino(payload: dict = Depends(require_modulo("notificaciones"))):
    """Catálogo de roles con etiqueta capitalizada (para UI)."""
    return {
        "roles": [{"id": r, "label": etiqueta_rol(r)} for r in ROLES_VALIDOS],
    }


@router.post("/")
def crear_manual(
    datos: dict,
    payload: dict = Depends(require_modulo("notificaciones")),
):
    if payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Solo Administrador puede crear notificaciones manuales")
    canal = datos.get("canal") or ("ambos" if datos.get("enviar_email") else "in_app")
    roles = datos.get("roles") or datos.get("rol")
    if roles:
        return {
            "mensaje": "Notificaciones emitidas por rol",
            "creadas": emitir_a_roles(
                datos.get("titulo", "Aviso"),
                datos.get("mensaje", ""),
                datos.get("tipo", "info"),
                roles=roles,
                canal=canal,
                destino_email=datos.get("destino_email"),
            ),
        }
    return emitir(
        datos.get("titulo", "Aviso"),
        datos.get("mensaje", ""),
        datos.get("tipo", "info"),
        destinatario_tipo=datos.get("destinatario_tipo") or "rol",
        destinatario=datos.get("destinatario") or "administrador",
        canal=canal,
        destino_email=datos.get("destino_email"),
    )
