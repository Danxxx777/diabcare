from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Any
from nucleo.utilidades.Dependencias import require_modulo, require_escritura
from paquetes.facturacion import FacturacionServicio as S
from paquetes.facturacion import CajaServicio as C

router = APIRouter(prefix="/api", tags=["P16 Facturación"])

def _u(p): return p.get("correo") or p.get("email") or p.get("sub") or "sistema"
def _ok(r):
    if r.get("error"):
        raise HTTPException(400, detail=r["error"])
    return r
def _nf(r):
    if r.get("error"):
        raise HTTPException(404, detail=r["error"])
    return r

class FacturaIn(BaseModel):
    encounter_id: Optional[str] = None
    id_orden_venta: Optional[str] = None
    id_paciente: str = ""
    id_seguro: str = ""
    subtotal: float = Field(0, ge=0)
    descuento: float = Field(0, ge=0)
    iva: Optional[float] = None
    total: Optional[float] = None
    estado: str = "emitida"
    fecha: str = ""
    lineas: list[dict[str, Any]] = []

class PagoIn(BaseModel):
    monto: float = Field(..., gt=0)
    metodo: str = "efectivo"
    fecha: str = ""
    estado: str = "registrado"
    referencia: str = ""

class CatalogoIn(BaseModel):
    nombre: Optional[str] = None
    cobertura_pct: Optional[float] = None
    codigo: Optional[str] = None
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    activo: Optional[bool] = True

# Seguros
@router.get("/seguros")
def listar_seguros(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("facturacion"))):
    return S.seguros.listar(offset, limit, q=q, q_campos=["nombre"], incluir_inactivos=True)

@router.get("/seguros/{id_seguro}")
def obtener_seguro(id_seguro: str, payload=Depends(require_modulo("facturacion"))):
    return _nf(S.seguros.obtener(id_seguro))

@router.post("/seguros")
def crear_seguro(d: CatalogoIn, payload=Depends(require_escritura("facturacion"))):
    r = _ok(S.seguros.crear({"nombre": d.nombre or "", "cobertura_pct": d.cobertura_pct or 0, "activo": True}))
    S.seguros.auditar(_u(payload), "create", f"Seguro {r.get('id_seguro')}", "facturacion"); return r

@router.put("/seguros/{id_seguro}")
def upd_seguro(id_seguro: str, d: CatalogoIn, payload=Depends(require_escritura("facturacion"))):
    r = _nf(S.seguros.actualizar(id_seguro, d.dict(exclude_none=True)))
    S.seguros.auditar(_u(payload), "update", f"Seguro {id_seguro}", "facturacion"); return r

@router.delete("/seguros/{id_seguro}")
def del_seguro(id_seguro: str, payload=Depends(require_escritura("facturacion"))):
    r = _nf(S.seguros.eliminar_logico(id_seguro))
    S.seguros.auditar(_u(payload), "delete", f"Seguro {id_seguro}", "facturacion"); return r

# Tarifario
@router.get("/tarifario")
def listar_tarifas(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("facturacion"))):
    return S.tarifario.listar(offset, limit, q=q, q_campos=["codigo", "descripcion"], incluir_inactivos=True)

@router.get("/tarifario/{id_tarifa}")
def obtener_tarifa(id_tarifa: str, payload=Depends(require_modulo("facturacion"))):
    return _nf(S.tarifario.obtener(id_tarifa))

@router.post("/tarifario")
def crear_tarifa(d: CatalogoIn, payload=Depends(require_escritura("facturacion"))):
    r = _ok(S.tarifario.crear({"codigo": d.codigo or "", "descripcion": d.descripcion or "", "precio": d.precio or 0, "activo": True}))
    S.tarifario.auditar(_u(payload), "create", f"Tarifa {r.get('id_tarifa')}", "facturacion"); return r

@router.put("/tarifario/{id_tarifa}")
def upd_tarifa(id_tarifa: str, d: CatalogoIn, payload=Depends(require_escritura("facturacion"))):
    r = _nf(S.tarifario.actualizar(id_tarifa, d.dict(exclude_none=True)))
    S.tarifario.auditar(_u(payload), "update", f"Tarifa {id_tarifa}", "facturacion"); return r

@router.delete("/tarifario/{id_tarifa}")
def del_tarifa(id_tarifa: str, payload=Depends(require_escritura("facturacion"))):
    r = _nf(S.tarifario.eliminar_logico(id_tarifa))
    S.tarifario.auditar(_u(payload), "delete", f"Tarifa {id_tarifa}", "facturacion"); return r

# Facturas
@router.get("/facturas")
def listar_facturas(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("facturacion"))):
    return S.listar_facturas(offset, limit, q=q)

@router.get("/facturacion/resumen")
def resumen_caja(payload=Depends(require_modulo("facturacion"))):
    return S.resumen_caja()

@router.post("/facturacion/seed")
def seed_facturacion(payload=Depends(require_escritura("facturacion"))):
    return S.seed_basico()

@router.get("/facturas/{id_factura}")
def obtener_factura(id_factura: str, payload=Depends(require_modulo("facturacion"))):
    return _nf(S.facturas.obtener(id_factura))

@router.post("/facturas")
def crear_factura(d: FacturaIn, payload=Depends(require_escritura("facturacion"))):
    r = _ok(S.crear_factura(d.dict()))
    S.facturas.auditar(_u(payload), "create", f"Factura {r.get('id_factura')}", "facturacion"); return r

@router.put("/facturas/{id_factura}")
def upd_factura(id_factura: str, d: FacturaIn, payload=Depends(require_escritura("facturacion"))):
    data = d.dict(exclude_none=True); data.pop("lineas", None)
    r = _nf(S.facturas.actualizar(id_factura, data))
    S.facturas.auditar(_u(payload), "update", f"Factura {id_factura}", "facturacion"); return r

@router.delete("/facturas/{id_factura}")
def del_factura(id_factura: str, payload=Depends(require_escritura("facturacion"))):
    r = _nf(S.facturas.eliminar_logico(id_factura))
    S.facturas.auditar(_u(payload), "delete", f"Factura {id_factura}", "facturacion"); return r

@router.get("/facturas/{id_factura}/pagos")
def pagos_factura(id_factura: str, payload=Depends(require_modulo("facturacion"))):
    return S.listar_pagos_factura(id_factura)

@router.get("/facturas/{id_factura}/comprobante")
def comprobante_factura(
    id_factura: str,
    formato: str = Query("html"),
    payload=Depends(require_modulo("facturacion")),
):
    """Factura/recibo imprimible para el cliente (consulta o farmacia)."""
    data = S.obtener_comprobante(id_factura)
    if data.get("error"):
        raise HTTPException(404, data["error"])
    if str(formato or "html").lower() == "json":
        return data
    from fastapi.responses import HTMLResponse
    return HTMLResponse(S.html_comprobante(data))

@router.post("/facturas/{id_factura}/pagos")
def crear_pago(id_factura: str, d: PagoIn, payload=Depends(require_escritura("facturacion"))):
    r = _ok(S.crear_pago(id_factura, d.dict()))
    S.pagos.auditar(_u(payload), "create", f"Pago factura {id_factura}", "facturacion"); return r

@router.get("/pagos/publico/{token}")
def pago_publico(token: str):
    r = S.publico_pago(token)
    if r.get("error"):
        raise HTTPException(404, detail=r["error"])
    return r

@router.post("/pagos/publico/{token}/checkout")
def pago_publico_checkout(token: str):
    r = S.iniciar_checkout_stripe(token)
    if r.get("error"):
        raise HTTPException(400, detail=r["error"])
    return r

class StripeConfirmIn(BaseModel):
    session_id: str = ""

@router.post("/pagos/publico/{token}/confirmar")
def pago_publico_confirmar(token: str, d: StripeConfirmIn):
    r = S.confirmar_checkout_stripe(token, d.session_id)
    if r.get("error"):
        raise HTTPException(400, detail=r["error"])
    return r

@router.post("/pagos/publico/{token}/simular")
def pago_publico_simular(token: str):
    """Cobro de demostracion desde el celular cuando no hay pasarela real."""
    r = S.simular_pago(token)
    if r.get("error"):
        raise HTTPException(400, detail=r["error"])
    return r


# ── Turno de caja ──────────────────────────────────────────────────────────
class AperturaIn(BaseModel):
    fondo_inicial: float = Field(0.0, ge=0)
    notas: str = ""


class CierreIn(BaseModel):
    contado_efectivo: float = Field(0.0, ge=0)
    notas: str = ""


@router.get("/caja/estado")
def caja_estado(payload=Depends(require_modulo("facturacion"))):
    """Turno vigente con lo acumulado, o caja cerrada."""
    return C.estado_caja()


@router.post("/caja/abrir")
def caja_abrir(d: AperturaIn, payload=Depends(require_escritura("facturacion"))):
    return _ok(C.abrir_turno(_u(payload), d.fondo_inicial, d.notas))


@router.post("/caja/cerrar")
def caja_cerrar(d: CierreIn, payload=Depends(require_escritura("facturacion"))):
    """Arqueo: el esperado lo calcula el sistema, solo se declara lo contado."""
    return _ok(C.cerrar_turno(_u(payload), d.contado_efectivo, d.notas))


@router.get("/caja/historial")
def caja_historial(limite: int = Query(30, ge=1, le=200),
                   payload=Depends(require_modulo("facturacion"))):
    return C.historial(limite)

@router.get("/pagos/{id_pago}")
def obtener_pago(id_pago: str, payload=Depends(require_modulo("facturacion"))):
    return _nf(S.pagos.obtener(id_pago))

@router.put("/pagos/{id_pago}")
def upd_pago(id_pago: str, d: PagoIn, payload=Depends(require_escritura("facturacion"))):
    r = _nf(S.pagos.actualizar(id_pago, d.dict(exclude_none=True)))
    S.pagos.auditar(_u(payload), "update", f"Pago {id_pago}", "facturacion"); return r

@router.delete("/pagos/{id_pago}")
def del_pago(id_pago: str, payload=Depends(require_escritura("facturacion"))):
    r = _nf(S.pagos.eliminar_logico(id_pago))
    S.pagos.auditar(_u(payload), "delete", f"Pago {id_pago}", "facturacion"); return r
