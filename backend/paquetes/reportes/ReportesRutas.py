from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import os

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.reportes.ReportesServicio import (
    generar_y_subir,
    listar_reportes,
    descargar_reporte,
    eliminar_reporte,
    eliminar_historial_reportes,
    verificar_reporte,
    pdf_por_codigo,
)

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])


class FiltroReporte(BaseModel):
    # Alcance del informe
    tipo: Optional[str] = "completo"          # simple | compuesto | completo
    departamento: Optional[str] = "todos"     # todos | citas | urgencias | ...
    # Filtros clínicos opcionales (solo aportan en tipo=completo)
    year: Optional[int] = None
    location: Optional[str] = None
    diabetes: Optional[int] = None
    gender: Optional[str] = None
    age_min: Optional[float] = None
    age_max: Optional[float] = None


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


def _base_desde_request(request: Request) -> str:
    from nucleo.utilidades.UrlPublica import base_publica
    return base_publica(str(request.base_url).rstrip("/"))


@router.post("/generar")
def generar(
    request: Request,
    filtros: Optional[FiltroReporte] = None,
    payload: dict = Depends(require_modulo("reportes")),
):
    f = filtros.dict(exclude_none=True) if filtros else {}
    tipo = str(f.get("tipo") or "completo").lower()
    if tipo not in ("simple", "compuesto", "completo"):
        raise HTTPException(status_code=400, detail="tipo inválido. Use: simple, compuesto o completo")
    f["tipo"] = tipo
    depto = str(f.get("departamento") or "todos").lower()
    f["departamento"] = depto if depto else "todos"
    if f.get("year") is not None and f["year"] < 0:
        raise HTTPException(status_code=400, detail="El año no puede ser negativo.")
    if f.get("age_min") is not None and f["age_min"] < 0:
        raise HTTPException(status_code=400, detail="La edad mínima no puede ser negativa.")
    if f.get("age_max") is not None and f["age_max"] < 0:
        raise HTTPException(status_code=400, detail="La edad máxima no puede ser negativa.")
    if (f.get("age_min") is not None and f.get("age_max") is not None
            and f["age_max"] < f["age_min"]):
        raise HTTPException(status_code=400, detail="La edad máxima no puede ser menor que la mínima.")
    try:
        return generar_y_subir(f, _usuario(payload), base_url=_base_desde_request(request))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo generar el reporte: {e}")


@router.get("/")
def listar(payload: dict = Depends(require_modulo("reportes"))):
    return {"reportes": listar_reportes()}


# ── Verificación pública (celular / QR, sin login) ──
@router.get("/verificar/{codigo}")
def verificar_publico(codigo: str):
    """Valida el código del pie/QR y devuelve metadatos del informe."""
    return verificar_reporte(codigo)


@router.get("/verificar/{codigo}/pdf")
def pdf_publico(codigo: str):
    """Abre el PDF si el código es válido (inline para verlo en el celular)."""
    contenido, nombre = pdf_por_codigo(codigo)
    if contenido is None:
        raise HTTPException(status_code=404, detail="Código no válido o reporte no encontrado")
    safe = nombre or f"{codigo}.pdf"
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{safe}"',
            "Cache-Control": "no-store",
        },
    )


@router.delete("/historial")
@router.post("/vaciar-historial")
def vaciar_historial(payload: dict = Depends(require_modulo("reportes"))):
    """Vacía todo el historial de PDFs. DELETE /historial o POST /vaciar-historial."""
    try:
        return eliminar_historial_reportes(_usuario(payload))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo vaciar el historial: {e}")


@router.delete("/{nombre}")
def eliminar(nombre: str, payload: dict = Depends(require_modulo("reportes"))):
    # Evita que "historial" se interprete como nombre de archivo si la ruta
    # estática no estaba cargada (servidor sin reiniciar).
    if nombre.strip().lower() in ("historial", "vaciar-historial"):
        try:
            return eliminar_historial_reportes(_usuario(payload))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"No se pudo vaciar el historial: {e}")
    if not eliminar_reporte(nombre, _usuario(payload)):
        raise HTTPException(status_code=404, detail="Reporte no encontrado o nombre inválido")
    return {"ok": True, "nombre": nombre}


@router.get("/{nombre}")
def descargar(nombre: str, payload: dict = Depends(require_modulo("reportes"))):
    contenido = descargar_reporte(nombre)
    if contenido is None:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
