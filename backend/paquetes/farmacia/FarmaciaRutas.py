from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from datetime import date
from nucleo.utilidades.Dependencias import require_modulo, require_escritura
from paquetes.farmacia import FarmaciaServicio as S

router = APIRouter(prefix="/api", tags=["P17 Farmacia"])

def _u(p): return p.get("correo") or p.get("email") or p.get("sub") or "sistema"
def _ok(r):
    if r.get("error"): raise HTTPException(400, detail=r["error"])
    return r
def _nf(r):
    if r.get("error"): raise HTTPException(404, detail=r["error"])
    return r

class MedIn(BaseModel):
    nombre: str = ""
    principio_activo: str = ""
    forma: str = "unidad"
    precio_venta: float = 0
    precio_costo: float = 0
    stock_minimo: float = 0
    venta_libre: bool = False
    activo: Optional[bool] = True

class RecetaIn(BaseModel):
    id_paciente: str
    id_medico: str = ""
    encounter_id: str = ""
    indicaciones: str = ""
    estado: str = "emitida"
    fecha: str = ""

class InventarioIn(BaseModel):
    id_medicamento: str
    lote: str = ""
    fecha_vencimiento: str = ""
    cantidad: float = 0
    costo_unitario: float = 0
    activo: Optional[bool] = True

class DispensarIn(BaseModel):
    id_receta: str = ""
    id_medicamento: str
    cantidad: float

class ProveedorIn(BaseModel):
    nombre: str = ""
    ruc: str = ""
    contacto: str = ""
    condiciones_pago: str = ""
    activo: Optional[bool] = True

class CompraIn(BaseModel):
    id_proveedor: str
    fecha_compra: str = ""
    estado: str = "pendiente"
    fecha_vencimiento_pago: str = ""
    lineas: list[dict[str, Any]] = []

class VentaIn(BaseModel):
    id_paciente: str = ""
    tipo: str = "venta_libre"
    id_receta: str = ""
    id_factura: str = ""
    descuento: float = 0
    fecha: str = ""
    lineas: list[dict[str, Any]] = []

class NotaIn(BaseModel):
    tipo: str = "credito"
    id_venta: str = ""
    id_compra: str = ""
    motivo: str = ""
    monto: float = 0
    fecha: str = ""
    estado: str = "registrada"

class CxpIn(BaseModel):
    id_compra: str = ""
    monto_pendiente: float = 0
    fecha_vencimiento: str = ""
    estado: str = "vigente"

class CierreIn(BaseModel):
    fecha: str = ""
    id_personal: str = ""
    total_ventas_efectivo: float = 0
    total_ventas_tarjeta: float = 0
    total_ventas_seguro: float = 0
    monto_esperado: float = 0
    monto_contado: float = 0

# Medicamentos
@router.get("/medicamentos")
def list_meds(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("farmacia"))):
    return S.medicamentos.listar(offset, limit, q=q, q_campos=["nombre", "principio_activo"], incluir_inactivos=True)

@router.get("/medicamentos/{id_medicamento}")
def get_med(id_medicamento: str, payload=Depends(require_modulo("farmacia"))):
    return _nf(S.medicamentos.obtener(id_medicamento))

@router.post("/medicamentos")
def post_med(d: MedIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _ok(S.medicamentos.crear(d.dict()))
    S.medicamentos.auditar(_u(payload), "create", f"Med {r.get('id_medicamento')}", "farmacia"); return r

@router.put("/medicamentos/{id_medicamento}")
def put_med(id_medicamento: str, d: MedIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.medicamentos.actualizar(id_medicamento, d.dict(exclude_none=True)))
    S.medicamentos.auditar(_u(payload), "update", f"Med {id_medicamento}", "farmacia"); return r

@router.delete("/medicamentos/{id_medicamento}")
def del_med(id_medicamento: str, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.medicamentos.eliminar_logico(id_medicamento))
    S.medicamentos.auditar(_u(payload), "delete", f"Med {id_medicamento}", "farmacia"); return r

# Recetas (escritura: médico; lectura mostrador: farmacia)
@router.get("/recetas")
def list_rec(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("recetas"))):
    return S.listar_recetas(
        offset=offset, limit=limit, q=q,
        q_campos=["id_paciente", "indicaciones", "estado", "fecha"],
        incluir_inactivos=True,
    )

@router.get("/recetas/{id_receta}")
def get_rec(id_receta: str, payload=Depends(require_modulo("recetas"))):
    r = _nf(S.recetas.obtener(id_receta))
    enriq = S.enriquecer_recetas([r])
    return enriq[0] if enriq else r

@router.post("/recetas")
def post_rec(d: RecetaIn, payload=Depends(require_modulo("recetas"))):
    data = d.dict()
    data.setdefault("id_medico", payload.get("sub") or "")
    # Médico emite; farmacia marca dispensada al despachar
    if str(data.get("estado") or "").lower() in ("", "pendiente", "dispensada"):
        data["estado"] = "emitida"
    if not data.get("fecha"):
        data["fecha"] = date.today().isoformat()
    r = _ok(S.recetas.crear(data))
    S.recetas.auditar(_u(payload), "create", f"Receta {r.get('id_receta')}", "farmacia")
    try:
        from paquetes.notificaciones.NotificacionesServicio import emitir_a_roles
        rid = r.get("id_receta") or ""
        emitir_a_roles(
            "Nueva receta para dispensar",
            f"Receta emitida pendiente en mostrador (id {rid}).",
            "info",
            roles=["farmaceutico"],
            referencia_tipo="receta",
            referencia_id=str(rid),
        )
    except Exception:
        pass
    return r

@router.put("/recetas/{id_receta}")
def put_rec(id_receta: str, d: RecetaIn, payload=Depends(require_modulo("recetas"))):
    r = _nf(S.recetas.actualizar(id_receta, d.dict(exclude_none=True)))
    S.recetas.auditar(_u(payload), "update", f"Receta {id_receta}", "farmacia"); return r

@router.delete("/recetas/{id_receta}")
def del_rec(id_receta: str, payload=Depends(require_modulo("recetas"))):
    r = _nf(S.recetas.eliminar_logico(id_receta))
    S.recetas.auditar(_u(payload), "delete", f"Receta {id_receta}", "farmacia"); return r

@router.get("/farmacia/recetas")
def list_rec_mostrador(
    offset: int = 0, limit: int = 50, q: str = "", estado: str = "",
    payload=Depends(require_modulo("farmacia")),
):
    """Recetas visibles en mostrador (dispensar / venta con Rx)."""
    return S.listar_recetas_mostrador(offset, limit, q=q, estado=estado)

@router.get("/farmacia/recetas/{id_receta}")
def get_rec_mostrador(id_receta: str, payload=Depends(require_modulo("farmacia"))):
    return _nf(S.recetas.obtener(id_receta))

# Inventario
@router.get("/farmacia/inventario")
def list_inv(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("farmacia"))):
    return S.inventario.listar(offset, limit, q=q, q_campos=["lote", "id_medicamento"], incluir_inactivos=True)

@router.get("/farmacia/inventario/{id_inventario}")
def get_inv(id_inventario: str, payload=Depends(require_modulo("farmacia"))):
    return _nf(S.inventario.obtener(id_inventario))

@router.post("/farmacia/inventario")
def post_inv(d: InventarioIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _ok(S.inventario.crear(d.dict()))
    S.inventario.auditar(_u(payload), "create", f"Inv {r.get('id_inventario')}", "farmacia"); return r

@router.put("/farmacia/inventario/{id_inventario}")
def put_inv(id_inventario: str, d: InventarioIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.inventario.actualizar(id_inventario, d.dict(exclude_none=True)))
    S.inventario.auditar(_u(payload), "update", f"Inv {id_inventario}", "farmacia"); return r

@router.delete("/farmacia/inventario/{id_inventario}")
def del_inv(id_inventario: str, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.inventario.eliminar_logico(id_inventario))
    S.inventario.auditar(_u(payload), "delete", f"Inv {id_inventario}", "farmacia"); return r

# Dispensaciones
@router.post("/farmacia/dispensar")
def post_disp(d: DispensarIn, payload=Depends(require_modulo("farmacia"))):
    r = _ok(S.dispensar(d.dict()))
    S.dispensaciones.auditar(_u(payload), "create", "Dispensación", "farmacia"); return r

@router.get("/farmacia/dispensaciones")
def list_disp(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("farmacia"))):
    return S.dispensaciones.listar(offset, limit, incluir_inactivos=True)

@router.get("/farmacia/dispensaciones/{id_dispensacion}")
def get_disp(id_dispensacion: str, payload=Depends(require_modulo("farmacia"))):
    return _nf(S.dispensaciones.obtener(id_dispensacion))

@router.put("/farmacia/dispensaciones/{id_dispensacion}")
def put_disp(id_dispensacion: str, d: DispensarIn, payload=Depends(require_modulo("farmacia"))):
    r = _nf(S.dispensaciones.actualizar(id_dispensacion, d.dict(exclude_none=True)))
    S.dispensaciones.auditar(_u(payload), "update", f"Disp {id_dispensacion}", "farmacia"); return r

@router.delete("/farmacia/dispensaciones/{id_dispensacion}")
def del_disp(id_dispensacion: str, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.dispensaciones.eliminar_logico(id_dispensacion))
    S.dispensaciones.auditar(_u(payload), "delete", f"Disp {id_dispensacion}", "farmacia"); return r

# Proveedores
@router.get("/proveedores")
def list_prov(offset: int = 0, limit: int = 50, q: str = "", payload=Depends(require_modulo("farmacia"))):
    return S.proveedores.listar(offset, limit, q=q, q_campos=["nombre", "ruc"], incluir_inactivos=True)

@router.get("/proveedores/{id_proveedor}")
def get_prov(id_proveedor: str, payload=Depends(require_modulo("farmacia"))):
    return _nf(S.proveedores.obtener(id_proveedor))

@router.post("/proveedores")
def post_prov(d: ProveedorIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _ok(S.proveedores.crear(d.dict()))
    S.proveedores.auditar(_u(payload), "create", f"Prov {r.get('id_proveedor')}", "farmacia"); return r

@router.put("/proveedores/{id_proveedor}")
def put_prov(id_proveedor: str, d: ProveedorIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.proveedores.actualizar(id_proveedor, d.dict(exclude_none=True)))
    S.proveedores.auditar(_u(payload), "update", f"Prov {id_proveedor}", "farmacia"); return r

@router.delete("/proveedores/{id_proveedor}")
def del_prov(id_proveedor: str, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.proveedores.eliminar_logico(id_proveedor))
    S.proveedores.auditar(_u(payload), "delete", f"Prov {id_proveedor}", "farmacia"); return r

# Compras
@router.get("/farmacia/compras")
def list_com(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("farmacia"))):
    return S.listar_compras(offset=offset, limit=limit, incluir_inactivos=True)

@router.get("/farmacia/compras/{id_compra}")
def get_com(id_compra: str, payload=Depends(require_modulo("farmacia"))):
    return _nf(S.compras.obtener(id_compra))

@router.post("/farmacia/compras")
def post_com(d: CompraIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _ok(S.registrar_compra(d.dict()))
    S.compras.auditar(_u(payload), "create", f"Compra {r.get('id_compra')}", "farmacia"); return r

@router.put("/farmacia/compras/{id_compra}")
def put_com(id_compra: str, d: CompraIn, payload=Depends(require_escritura("farmacia_caja"))):
    data = d.dict(exclude_none=True); data.pop("lineas", None)
    r = _nf(S.compras.actualizar(id_compra, data))
    S.compras.auditar(_u(payload), "update", f"Compra {id_compra}", "farmacia"); return r

@router.delete("/farmacia/compras/{id_compra}")
def del_com(id_compra: str, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.compras.eliminar_logico(id_compra))
    S.compras.auditar(_u(payload), "delete", f"Compra {id_compra}", "farmacia"); return r

@router.get("/farmacia/margen")
def get_margen(payload=Depends(require_modulo("farmacia"))):
    return S.resumen_margen()

@router.get("/farmacia/resumen")
def get_resumen_farmacia(payload=Depends(require_modulo("farmacia"))):
    return S.resumen_operativo()

# Ventas
@router.get("/farmacia/ventas")
def list_ven(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("farmacia"))):
    return S.listar_ventas(offset=offset, limit=limit, incluir_inactivos=True)

@router.get("/farmacia/ventas/{id_venta}")
def get_ven(id_venta: str, payload=Depends(require_modulo("farmacia"))):
    return _nf(S.ventas.obtener(id_venta))

@router.get("/farmacia/ventas/{id_venta}/comprobante")
def comprobante_venta(
    id_venta: str,
    formato: str = "html",
    payload=Depends(require_modulo("farmacia")),
):
    """Recibo de farmacia para el cliente (usa la factura emitida al vender)."""
    data = S.comprobante_venta(id_venta)
    if data.get("error"):
        raise HTTPException(404, data["error"])
    if str(formato or "html").lower() == "json":
        return data
    from fastapi.responses import HTMLResponse
    from paquetes.facturacion.FacturacionServicio import html_comprobante
    return HTMLResponse(html_comprobante(data))

@router.post("/farmacia/ventas")
def post_ven(d: VentaIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _ok(S.registrar_venta(d.dict()))
    S.ventas.auditar(_u(payload), "create", f"Venta {r.get('id_venta')}", "farmacia"); return r

@router.put("/farmacia/ventas/{id_venta}")
def put_ven(id_venta: str, d: VentaIn, payload=Depends(require_escritura("farmacia_caja"))):
    data = d.dict(exclude_none=True); data.pop("lineas", None)
    r = _nf(S.ventas.actualizar(id_venta, data))
    S.ventas.auditar(_u(payload), "update", f"Venta {id_venta}", "farmacia"); return r

@router.delete("/farmacia/ventas/{id_venta}")
def del_ven(id_venta: str, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.ventas.eliminar_logico(id_venta))
    S.ventas.auditar(_u(payload), "delete", f"Venta {id_venta}", "farmacia"); return r

@router.get("/farmacia/kardex")
def list_kardex(offset: int = 0, limit: int = 100, payload=Depends(require_modulo("farmacia"))):
    return S.kardex.listar(offset, limit, incluir_inactivos=True, orden="creado_en")

# Notas
@router.get("/farmacia/notas-credito")
def list_notas(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("farmacia"))):
    return S.notas.listar(offset, limit, incluir_inactivos=True)

@router.get("/farmacia/notas-credito/{id_nota}")
def get_nota(id_nota: str, payload=Depends(require_modulo("farmacia"))):
    return _nf(S.notas.obtener(id_nota))

@router.post("/farmacia/notas-credito")
def post_nota(d: NotaIn, payload=Depends(require_escritura("farmacia_caja"))):
    if not d.id_venta and not d.id_compra:
        raise HTTPException(400, detail="RN-FARM-010: nota debe referenciar venta o compra")
    r = _ok(S.notas.crear(d.dict()))
    S.notas.auditar(_u(payload), "create", f"Nota {r.get('id_nota')}", "farmacia"); return r

@router.put("/farmacia/notas-credito/{id_nota}")
def put_nota(id_nota: str, d: NotaIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.notas.actualizar(id_nota, d.dict(exclude_none=True)))
    S.notas.auditar(_u(payload), "update", f"Nota {id_nota}", "farmacia"); return r

@router.delete("/farmacia/notas-credito/{id_nota}")
def del_nota(id_nota: str, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.notas.eliminar_logico(id_nota))
    S.notas.auditar(_u(payload), "delete", f"Nota {id_nota}", "farmacia"); return r

# CxP (operación de farmacia / compras — no exige módulo facturación)
@router.get("/farmacia/cuentas-por-pagar")
def list_cxp(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("farmacia"))):
    return S.listar_cxp(offset=offset, limit=limit, incluir_inactivos=True)

@router.get("/farmacia/cuentas-por-pagar/{id_cxp}")
def get_cxp(id_cxp: str, payload=Depends(require_modulo("farmacia"))):
    return _nf(S.cxp.obtener(id_cxp))

@router.post("/farmacia/cuentas-por-pagar")
def post_cxp(d: CxpIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _ok(S.cxp.crear(d.dict()))
    S.cxp.auditar(_u(payload), "create", f"CxP {r.get('id_cxp')}", "farmacia"); return r

@router.put("/farmacia/cuentas-por-pagar/{id_cxp}")
def put_cxp(id_cxp: str, d: CxpIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.cxp.actualizar(id_cxp, d.dict(exclude_none=True)))
    S.cxp.auditar(_u(payload), "update", f"CxP {id_cxp}", "farmacia"); return r

@router.delete("/farmacia/cuentas-por-pagar/{id_cxp}")
def del_cxp(id_cxp: str, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.cxp.eliminar_logico(id_cxp))
    S.cxp.auditar(_u(payload), "delete", f"CxP {id_cxp}", "farmacia"); return r

# Cierre caja
@router.get("/farmacia/cierre-caja")
def list_cierre(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("farmacia"))):
    return S.listar_cierres(offset=offset, limit=limit, incluir_inactivos=True)

@router.get("/farmacia/cierre-caja/{id_cierre}")
def get_cierre(id_cierre: str, payload=Depends(require_modulo("farmacia"))):
    return _nf(S.cierres.obtener(id_cierre))

@router.post("/farmacia/cierre-caja")
def post_cierre(d: CierreIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _ok(S.cierre_caja(d.dict()))
    S.cierres.auditar(_u(payload), "create", f"Cierre {r.get('id_cierre')} dif={r.get('registro',{}).get('diferencia')}", "farmacia")
    return r

@router.put("/farmacia/cierre-caja/{id_cierre}")
def put_cierre(id_cierre: str, d: CierreIn, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.cierres.actualizar(id_cierre, d.dict(exclude_none=True)))
    S.cierres.auditar(_u(payload), "update", f"Cierre {id_cierre}", "farmacia"); return r

@router.delete("/farmacia/cierre-caja/{id_cierre}")
def del_cierre(id_cierre: str, payload=Depends(require_escritura("farmacia_caja"))):
    r = _nf(S.cierres.eliminar_logico(id_cierre))
    S.cierres.auditar(_u(payload), "delete", f"Cierre {id_cierre}", "farmacia"); return r

@router.get("/farmacia/comprobantes")
def list_comp(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("facturacion"))):
    return S.comprobantes.listar(offset, limit, incluir_inactivos=True)

@router.post("/farmacia/seed")
def seed(payload=Depends(require_escritura("farmacia_caja"))):
    S.seed_basico()
    return {"mensaje": "seed farmacia ok"}
