"""P17 Farmacia — medicamentos, recetas, inventario, compras, ventas, kardex, caja."""
from __future__ import annotations
from datetime import datetime, date
from nucleo.utilidades.ParquetStore import ParquetStore
from nucleo.utilidades.PacientesLookup import mapa_pacientes

_SIN_TOPE = 10**9

ESTADOS_RECETA = {
    "emitida": "Emitida",
    "pendiente": "Pendiente",
    "dispensada": "Dispensada",
    "anulada": "Anulada",
    "anulado": "Anulada",
}


def _now():
    return datetime.utcnow().isoformat()

medicamentos = ParquetStore(
    "negocio/dim_medicamento.parquet",
    ["id_medicamento", "nombre", "principio_activo", "forma", "precio_venta", "precio_costo",
     "stock_minimo", "venta_libre", "activo", "creado_en", "actualizado_en"],
    "id_medicamento", "medicamentos", modo_borrado="activo",
)
recetas = ParquetStore(
    "negocio/oper_recetas.parquet",
    ["id_receta", "id_paciente", "id_medico", "encounter_id", "indicaciones", "estado",
     "fecha", "creado_en", "actualizado_en"],
    "id_receta", "recetas", modo_borrado="estado", valor_anulado="anulada",
)
inventario = ParquetStore(
    "negocio/oper_inventario.parquet",
    ["id_inventario", "id_medicamento", "lote", "fecha_vencimiento", "cantidad", "costo_unitario",
     "activo", "creado_en", "actualizado_en"],
    "id_inventario", "lotes", modo_borrado="activo",
)
dispensaciones = ParquetStore(
    "negocio/hechos_farmacia_dispensacion.parquet",
    ["id_dispensacion", "id_receta", "id_medicamento", "id_inventario", "cantidad", "lote",
     "fecha", "estado", "creado_en", "actualizado_en"],
    "id_dispensacion", "dispensaciones", modo_borrado="estado",
)
proveedores = ParquetStore(
    "negocio/dim_proveedor.parquet",
    ["id_proveedor", "nombre", "ruc", "contacto", "condiciones_pago", "activo", "creado_en", "actualizado_en"],
    "id_proveedor", "proveedores", modo_borrado="activo",
)
compras = ParquetStore(
    "negocio/oper_compras.parquet",
    ["id_compra", "id_proveedor", "fecha_compra", "total", "estado", "creado_en", "actualizado_en"],
    "id_compra", "compras", modo_borrado="estado", valor_anulado="anulada",
)
compras_detalle = ParquetStore(
    "negocio/oper_compras_detalle.parquet",
    ["id_detalle", "id_compra", "id_medicamento", "cantidad", "precio_unitario", "lote",
     "fecha_vencimiento", "creado_en", "actualizado_en"],
    "id_detalle", "detalles_compra", modo_borrado="estado",
)
movimientos = ParquetStore(
    "negocio/oper_movimientos_inventario.parquet",
    ["id_movimiento", "id_medicamento", "tipo", "cantidad", "fecha", "referencia", "creado_en", "actualizado_en"],
    "id_movimiento", "movimientos", modo_borrado="estado",
)
impuestos = ParquetStore(
    "negocio/dim_impuesto.parquet",
    ["id_impuesto", "nombre", "porcentaje", "vigente_desde", "activo", "creado_en", "actualizado_en"],
    "id_impuesto", "impuestos", modo_borrado="activo",
)
ordenes_venta = ParquetStore(
    "negocio/oper_ordenes_venta.parquet",
    ["id_orden_venta", "id_paciente", "tipo", "id_receta", "fecha", "estado", "creado_en", "actualizado_en"],
    "id_orden_venta", "ordenes_venta", modo_borrado="estado",
)
ordenes_venta_det = ParquetStore(
    "negocio/oper_ordenes_venta_detalle.parquet",
    ["id_detalle", "id_orden_venta", "id_medicamento", "cantidad", "precio_unitario", "subtotal",
     "creado_en", "actualizado_en"],
    "id_detalle", "detalles_venta", modo_borrado="estado",
)
ventas = ParquetStore(
    "negocio/hechos_venta_farmacia.parquet",
    ["id_venta", "id_orden_venta", "id_factura", "total_bruto", "descuento", "iva", "total_neto",
     "fecha", "estado", "creado_en", "actualizado_en"],
    "id_venta", "ventas", modo_borrado="estado",
)
cxp = ParquetStore(
    "negocio/oper_cuentas_por_pagar.parquet",
    ["id_cxp", "id_compra", "monto_pendiente", "fecha_vencimiento", "estado", "creado_en", "actualizado_en"],
    "id_cxp", "cuentas_por_pagar", modo_borrado="estado",
)
notas = ParquetStore(
    "negocio/oper_notas_credito_debito.parquet",
    ["id_nota", "tipo", "id_venta", "id_compra", "motivo", "monto", "fecha", "estado", "creado_en", "actualizado_en"],
    "id_nota", "notas", modo_borrado="estado",
)
kardex = ParquetStore(
    "negocio/oper_kardex.parquet",
    ["id_movimiento_kardex", "id_medicamento", "fecha", "tipo_movimiento", "cantidad", "costo_unitario",
     "costo_total", "saldo_cantidad", "saldo_valorizado", "referencia", "creado_en", "actualizado_en"],
    "id_movimiento_kardex", "kardex", modo_borrado="estado",
)
comprobantes = ParquetStore(
    "negocio/oper_comprobantes_electronicos.parquet",
    ["id_comprobante", "id_factura", "tipo", "autorizacion_sri", "clave_acceso", "fecha_autorizacion",
     "estado", "creado_en", "actualizado_en"],
    "id_comprobante", "comprobantes", modo_borrado="estado",
)
cierres = ParquetStore(
    "negocio/oper_cierre_caja.parquet",
    ["id_cierre", "fecha", "id_personal", "total_ventas_efectivo", "total_ventas_tarjeta",
     "total_ventas_seguro", "monto_esperado", "monto_contado", "diferencia", "estado",
     "creado_en", "actualizado_en"],
    "id_cierre", "cierres", modo_borrado="estado",
)
margen_agg = ParquetStore(
    "negocio/agg_margen_farmacia.parquet",
    ["id_agg", "id_medicamento", "periodo", "ingreso_total", "costo_total", "margen",
     "creado_en", "actualizado_en"],
    "id_agg", "margenes", modo_borrado="activo",
)

def _iva_vigente() -> float:
    r = impuestos.listar(limit=20, filtros={"nombre": "IVA"})
    rows = r.get("impuestos") or []
    if not rows:
        return 15.0
    rows = sorted(rows, key=lambda x: str(x.get("vigente_desde") or ""), reverse=True)
    return float(rows[0].get("porcentaje") or 15)

def _lotes_fifo(id_medicamento: str):
    r = inventario.listar(limit=500, filtros={"id_medicamento": id_medicamento})
    lots = [x for x in (r.get("lotes") or []) if float(x.get("cantidad") or 0) > 0 and str(x.get("activo", True)).lower() not in ("false", "0")]
    today = date.today().isoformat()
    lots = sorted(lots, key=lambda x: str(x.get("fecha_vencimiento") or "9999"))
    return lots, today

def _kardex_append(id_medicamento: str, tipo: str, cantidad: float, costo_u: float, referencia: str):
    prev = kardex.listar(limit=500, filtros={"id_medicamento": id_medicamento}, incluir_inactivos=True)
    rows = prev.get("kardex") or []
    saldo_c = 0.0
    saldo_v = 0.0
    if rows:
        last = sorted(rows, key=lambda x: str(x.get("creado_en") or ""))[-1]
        saldo_c = float(last.get("saldo_cantidad") or 0)
        saldo_v = float(last.get("saldo_valorizado") or 0)
    if tipo == "entrada":
        saldo_c += cantidad
        saldo_v += cantidad * costo_u
    else:
        saldo_c -= cantidad
        saldo_v -= cantidad * costo_u
    return kardex.crear({
        "id_medicamento": id_medicamento,
        "fecha": _now()[:10],
        "tipo_movimiento": tipo,
        "cantidad": cantidad,
        "costo_unitario": costo_u,
        "costo_total": cantidad * costo_u,
        "saldo_cantidad": saldo_c,
        "saldo_valorizado": max(saldo_v, 0),
        "referencia": referencia,
        "estado": "registrado",
    })

def dispensar(datos: dict) -> dict:
    id_receta = str(datos.get("id_receta") or "")
    id_med = str(datos.get("id_medicamento") or "")
    cantidad = float(datos.get("cantidad") or 0)
    if cantidad <= 0:
        return {"error": "cantidad inválida"}
    med = medicamentos.obtener(id_med)
    if med.get("error"):
        return med
    venta_libre = str(med.get("venta_libre", False)).lower() in ("true", "1", "yes")
    if not id_receta and not venta_libre:
        return {"error": "RN-FARM-001: no se dispensa sin receta (salvo venta libre)"}
    if id_receta:
        rec = recetas.obtener(id_receta)
        if rec.get("error"):
            return rec
        if str(rec.get("estado") or "").lower() in ("anulada", "anulado"):
            return {"error": "receta anulada"}
    lots, today = _lotes_fifo(id_med)
    restante = cantidad
    usados = []
    for lot in lots:
        fv = str(lot.get("fecha_vencimiento") or "")
        if fv and fv < today:
            continue  # RN-FARM-004 skip expired
        disp = min(restante, float(lot.get("cantidad") or 0))
        if disp <= 0:
            continue
        nueva_cant = float(lot.get("cantidad") or 0) - disp
        inventario.actualizar(lot["id_inventario"], {"cantidad": nueva_cant})
        usados.append((lot, disp))
        restante -= disp
        if restante <= 0:
            break
    if restante > 0:
        return {"error": "RN-FARM-004/stock: sin lote vigente suficiente"}
    # create dispensation rows
    outs = []
    for lot, disp in usados:
        r = dispensaciones.crear({
            "id_receta": id_receta,
            "id_medicamento": id_med,
            "id_inventario": lot["id_inventario"],
            "cantidad": disp,
            "lote": lot.get("lote") or "",
            "fecha": _now()[:10],
            "estado": "dispensada",
        })
        movimientos.crear({
            "id_medicamento": id_med, "tipo": "salida", "cantidad": disp,
            "fecha": _now()[:10], "referencia": r.get("id_dispensacion") or "", "estado": "registrado",
        })
        _kardex_append(id_med, "salida", disp, float(lot.get("costo_unitario") or med.get("precio_costo") or 0), r.get("id_dispensacion") or "")
        outs.append(r)
        # stock mínimo
        total_stock = sum(float(x.get("cantidad") or 0) for x in _lotes_fifo(id_med)[0])
        if total_stock < float(med.get("stock_minimo") or 0):
            try:
                from paquetes.notificaciones.NotificacionesServicio import crear as notif_crear
                notif_crear({
                    "titulo": "Stock bajo",
                    "mensaje": f"Medicamento {med.get('nombre')} bajo mínimo ({total_stock})",
                    "tipo": "warning",
                })
            except Exception:
                pass
    if id_receta and outs:
        recetas.actualizar(id_receta, {"estado": "dispensada"})
    return {"mensaje": "dispensado", "dispensaciones": outs}

def registrar_compra(datos: dict) -> dict:
    lineas = datos.get("lineas") or []
    if not lineas:
        return {"error": "compra sin líneas"}
    total = sum(float(l.get("cantidad") or 0) * float(l.get("precio_unitario") or 0) for l in lineas)
    c = compras.crear({
        "id_proveedor": str(datos.get("id_proveedor") or ""),
        "fecha_compra": str(datos.get("fecha_compra") or _now()[:10]),
        "total": total,
        "estado": str(datos.get("estado") or "pendiente"),
    })
    if c.get("error"):
        return c
    cid = c["id_compra"]
    for ln in lineas:
        id_med = str(ln.get("id_medicamento") or "")
        cant = float(ln.get("cantidad") or 0)
        pu = float(ln.get("precio_unitario") or 0)
        lote = str(ln.get("lote") or "L1")
        fv = str(ln.get("fecha_vencimiento") or "")
        compras_detalle.crear({
            "id_compra": cid, "id_medicamento": id_med, "cantidad": cant,
            "precio_unitario": pu, "lote": lote, "fecha_vencimiento": fv,
            "estado": "registrado",
        })
        # RN-FARM-005 entrada inventario
        inventario.crear({
            "id_medicamento": id_med, "lote": lote, "fecha_vencimiento": fv,
            "cantidad": cant, "costo_unitario": pu, "activo": True,
        })
        movimientos.crear({
            "id_medicamento": id_med, "tipo": "entrada", "cantidad": cant,
            "fecha": _now()[:10], "referencia": cid, "estado": "registrado",
        })
        _kardex_append(id_med, "entrada", cant, pu, cid)
    cxp.crear({
        "id_compra": cid, "monto_pendiente": total,
        "fecha_vencimiento": str(datos.get("fecha_vencimiento_pago") or ""),
        "estado": "vigente",
    })
    return c

def registrar_venta(datos: dict) -> dict:
    lineas = datos.get("lineas") or []
    tipo = str(datos.get("tipo") or "venta_libre")
    id_receta = str(datos.get("id_receta") or "")
    if tipo == "con_receta" and not id_receta:
        return {"error": "venta con_receta requiere id_receta"}
    ov = ordenes_venta.crear({
        "id_paciente": str(datos.get("id_paciente") or ""),
        "tipo": tipo, "id_receta": id_receta,
        "fecha": str(datos.get("fecha") or _now()[:10]),
        "estado": "registrada",
    })
    if ov.get("error"):
        return ov
    oid = ov["id_orden_venta"]
    bruto = 0.0
    for ln in lineas:
        cant = float(ln.get("cantidad") or 1)
        pu = float(ln.get("precio_unitario") or 0)
        if pu <= 0:
            med0 = medicamentos.obtener(str(ln.get("id_medicamento") or ""))
            if not med0.get("error"):
                pu = float(med0.get("precio_venta") or 0)
                ln["precio_unitario"] = pu
        sub = cant * pu
        bruto += sub
        ordenes_venta_det.crear({
            "id_orden_venta": oid, "id_medicamento": str(ln.get("id_medicamento") or ""),
            "cantidad": cant, "precio_unitario": pu, "subtotal": sub, "estado": "registrado",
        })
        # stock out via dispensar-like for each line
        d = dispensar({
            "id_receta": id_receta if tipo == "con_receta" else "",
            "id_medicamento": str(ln.get("id_medicamento") or ""),
            "cantidad": cant,
        })
        if d.get("error"):
            return d
    pct = _iva_vigente()
    descuento = float(datos.get("descuento") or 0)
    base = max(bruto - descuento, 0)
    iva = round(base * pct / 100.0, 2)
    neto = round(base + iva, 2)
    v = ventas.crear({
        "id_orden_venta": oid,
        "id_factura": str(datos.get("id_factura") or ""),
        "total_bruto": bruto, "descuento": descuento, "iva": iva, "total_neto": neto,
        "fecha": _now()[:10], "estado": "registrada",
    })
    if v.get("error"):
        return v

    # Actualizar margen agregado del periodo (KPI dashboard)
    periodo = _now()[:7]
    for ln in lineas:
        id_med = str(ln.get("id_medicamento") or "")
        if not id_med:
            continue
        cant = float(ln.get("cantidad") or 1)
        pu = float(ln.get("precio_unitario") or 0)
        med = medicamentos.obtener(id_med)
        costo_u = float(med.get("precio_costo") or 0) if not med.get("error") else 0.0
        ingreso = cant * pu
        costo = cant * costo_u
        existentes = (margen_agg.listar(limit=200, filtros={"id_medicamento": id_med, "periodo": periodo}).get("margenes") or [])
        if existentes:
            row = existentes[0]
            ingreso_t = float(row.get("ingreso_total") or 0) + ingreso
            costo_t = float(row.get("costo_total") or 0) + costo
            margen_agg.actualizar(row["id_agg"], {
                "ingreso_total": ingreso_t,
                "costo_total": costo_t,
                "margen": round(ingreso_t - costo_t, 2),
            })
        else:
            margen_agg.crear({
                "id_medicamento": id_med,
                "periodo": periodo,
                "ingreso_total": ingreso,
                "costo_total": costo,
                "margen": round(ingreso - costo, 2),
            })

    # Emitir factura de mostrador vinculada a la orden (flujo negocio)
    emitir_fac = str(datos.get("emitir_factura") or "true").lower() not in ("false", "0", "no")
    if emitir_fac and not datos.get("id_factura"):
        try:
            from paquetes.facturacion.FacturacionServicio import crear_factura as emitir_factura
            fac_lineas = []
            for ln in lineas:
                cant = float(ln.get("cantidad") or 1)
                pu = float(ln.get("precio_unitario") or 0)
                med = medicamentos.obtener(str(ln.get("id_medicamento") or ""))
                concepto = med.get("nombre") if not med.get("error") else "Medicamento"
                fac_lineas.append({
                    "concepto": concepto,
                    "cantidad": cant,
                    "precio_unitario": pu,
                })
            fac = emitir_factura({
                "id_orden_venta": oid,
                "id_paciente": str(datos.get("id_paciente") or ""),
                "subtotal": bruto,
                "descuento": descuento,
                "iva": iva,
                "total": neto,
                "lineas": fac_lineas,
                "fecha": _now()[:10],
            })
            if not fac.get("error") and fac.get("id_factura"):
                ventas.actualizar(v["id_venta"], {"id_factura": fac["id_factura"]})
                v["id_factura"] = fac["id_factura"]
                comprobantes.crear({
                    "id_factura": fac["id_factura"],
                    "tipo": "factura",
                    "autorizacion_sri": "SIM-" + str(fac["id_factura"])[:8],
                    "clave_acceso": "DEMO" + _now().replace(":", "").replace("-", "")[:20],
                    "fecha_autorizacion": _now()[:10],
                    "estado": "autorizado",
                })
        except Exception:
            pass
    elif datos.get("id_factura"):
        # RN-FARM-008 simulate electronic voucher if factura linked
        comprobantes.crear({
            "id_factura": str(datos["id_factura"]),
            "tipo": "factura",
            "autorizacion_sri": "SIM-" + str(datos["id_factura"])[:8],
            "clave_acceso": "DEMO" + _now().replace(":", "").replace("-", "")[:20],
            "fecha_autorizacion": _now()[:10],
            "estado": "autorizado",
        })
    return v

def cierre_caja(datos: dict) -> dict:
    esperado = round(float(datos.get("monto_esperado") or 0), 2)
    contado = round(float(datos.get("monto_contado") or 0), 2)
    dif = round(contado - esperado, 2)
    return cierres.crear({
        "fecha": str(datos.get("fecha") or _now()[:10]),
        "id_personal": str(datos.get("id_personal") or ""),
        "total_ventas_efectivo": round(float(datos.get("total_ventas_efectivo") or 0), 2),
        "total_ventas_tarjeta": round(float(datos.get("total_ventas_tarjeta") or 0), 2),
        "total_ventas_seguro": round(float(datos.get("total_ventas_seguro") or 0), 2),
        "monto_esperado": esperado, "monto_contado": contado, "diferencia": dif,
        "estado": "cerrado",
    })


def _money(v) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def enriquecer_compras(filas: list) -> list:
    if not filas:
        return []
    prov = {}
    try:
        for p in (proveedores.listar(limit=_SIN_TOPE, incluir_inactivos=True).get("proveedores") or []):
            prov[str(p.get("id_proveedor") or "")] = str(p.get("nombre") or "").strip()
    except Exception:
        pass
    out = []
    for r in filas:
        x = dict(r)
        pid = str(x.get("id_proveedor") or "")
        x["proveedor_nombre"] = prov.get(pid) or (f"Proveedor {pid[:8]}…" if pid else "—")
        x["total"] = _money(x.get("total"))
        est = str(x.get("estado") or "").lower()
        x["estado_label"] = {
            "registrada": "Registrada", "registrado": "Registrado",
            "anulada": "Anulada", "anulado": "Anulado",
        }.get(est, est[:1].upper() + est[1:] if est else "—")
        out.append(x)
    return out


def listar_compras(**kwargs) -> dict:
    res = compras.listar(**kwargs)
    res["compras"] = enriquecer_compras(res.get("compras") or [])
    return res


def enriquecer_cxp(filas: list) -> list:
    if not filas:
        return []
    compras_map = {}
    try:
        for c in (compras.listar(limit=_SIN_TOPE, incluir_inactivos=True).get("compras") or []):
            compras_map[str(c.get("id_compra") or "")] = c
    except Exception:
        pass
    prov = {}
    try:
        for p in (proveedores.listar(limit=_SIN_TOPE, incluir_inactivos=True).get("proveedores") or []):
            prov[str(p.get("id_proveedor") or "")] = str(p.get("nombre") or "").strip()
    except Exception:
        pass
    out = []
    for r in filas:
        x = dict(r)
        cid = str(x.get("id_compra") or "")
        c = compras_map.get(cid) or {}
        pnombre = prov.get(str(c.get("id_proveedor") or ""), "")
        fecha = str(c.get("fecha_compra") or "")[:10]
        if pnombre and fecha:
            x["compra_label"] = f"{pnombre} · {fecha}"
        elif pnombre:
            x["compra_label"] = pnombre
        elif fecha:
            x["compra_label"] = f"Compra {fecha}"
        else:
            x["compra_label"] = f"Compra {cid[:8]}…" if cid else "—"
        x["proveedor_nombre"] = pnombre or "—"
        x["monto_pendiente"] = _money(x.get("monto_pendiente"))
        est = str(x.get("estado") or "").lower()
        x["estado_label"] = {
            "vigente": "Vigente", "pagada": "Pagada", "anulada": "Anulada", "anulado": "Anulado",
        }.get(est, est[:1].upper() + est[1:] if est else "—")
        out.append(x)
    return out


def listar_cxp(**kwargs) -> dict:
    res = cxp.listar(**kwargs)
    res["cuentas_por_pagar"] = enriquecer_cxp(res.get("cuentas_por_pagar") or [])
    return res


def enriquecer_cierres(filas: list) -> list:
    if not filas:
        return []
    out = []
    for r in filas:
        x = dict(r)
        for k in (
            "monto_esperado", "monto_contado", "diferencia",
            "total_ventas_efectivo", "total_ventas_tarjeta", "total_ventas_seguro",
        ):
            if k in x or x.get(k) is not None:
                x[k] = _money(x.get(k))
        est = str(x.get("estado") or "").lower()
        x["estado_label"] = {
            "cerrado": "Cerrado", "abierto": "Abierto", "anulado": "Anulado", "anulada": "Anulada",
        }.get(est, est[:1].upper() + est[1:] if est else "—")
        out.append(x)
    return out


def listar_cierres(**kwargs) -> dict:
    res = cierres.listar(**kwargs)
    res["cierres"] = enriquecer_cierres(res.get("cierres") or [])
    return res


def enriquecer_ventas(filas: list) -> list:
    if not filas:
        return []
    out = []
    for r in filas:
        x = dict(r)
        for k in ("total_bruto", "descuento", "iva", "total_neto"):
            if k in x or x.get(k) is not None:
                x[k] = _money(x.get(k))
        fid = str(x.get("id_factura") or "")
        x["factura_label"] = (fid[:8] + "…") if len(fid) > 10 else (fid or "—")
        est = str(x.get("estado") or "").lower()
        x["estado_label"] = {
            "registrada": "Registrada", "registrado": "Registrado",
            "anulada": "Anulada", "anulado": "Anulado",
        }.get(est, est[:1].upper() + est[1:] if est else "—")
        out.append(x)
    return out


def listar_ventas(**kwargs) -> dict:
    res = ventas.listar(**kwargs)
    res["ventas"] = enriquecer_ventas(res.get("ventas") or [])
    return res


def enriquecer_recetas(filas: list) -> list:
    if not filas:
        return []
    ids = {str(r.get("id_paciente") or "") for r in filas}
    mapa = mapa_pacientes(ids)
    out = []
    for r in filas:
        x = dict(r)
        pid = str(x.get("id_paciente") or "")
        p = mapa.get(pid) or {}
        nombre = (p.get("nombre_completo") or "").strip()
        doc = str(p.get("documento") or "").strip()
        x["paciente_nombre"] = nombre or (f"Paciente {pid[:8]}…" if pid else "—")
        x["documento"] = doc
        x["paciente_documento"] = doc
        x["paciente_label"] = x["paciente_nombre"]
        x["tiene_foto"] = bool(p.get("tiene_foto"))
        est = str(x.get("estado") or "").lower()
        x["estado_label"] = ESTADOS_RECETA.get(est, (est[:1].upper() + est[1:]) if est else "—")
        out.append(x)
    return out


def listar_recetas(**kwargs) -> dict:
    res = recetas.listar(**kwargs)
    res["recetas"] = enriquecer_recetas(res.get("recetas") or [])
    return res


def listar_recetas_mostrador(offset: int = 0, limit: int = 50, q: str = "", estado: str = "") -> dict:
    """Recetas para mostrador. Pagina sobre el universo completo (sin tope 1500)."""
    limit = max(1, min(int(limit or 50), 300))
    offset = max(0, int(offset or 0))
    filtros = {"estado": estado} if estado else None
    ql = str(q or "").strip().lower()

    if not ql:
        base = recetas.listar(
            offset=offset,
            limit=limit,
            filtros=filtros,
            incluir_inactivos=True,
            orden="fecha",
        )
        return {
            "total": int(base.get("total") or 0),
            "recetas": enriquecer_recetas(list(base.get("recetas") or [])),
        }

    base = recetas.listar(
        offset=0,
        limit=_SIN_TOPE,
        filtros=filtros,
        incluir_inactivos=True,
        orden="fecha",
    )
    rows = enriquecer_recetas(list(base.get("recetas") or []))
    toks = [t for t in ql.replace(",", " ").split() if len(t) >= 2]
    filtradas = []
    for item in rows:
        hay = " ".join([
            str(item.get("paciente_nombre") or ""),
            str(item.get("documento") or ""),
            str(item.get("indicaciones") or ""),
            str(item.get("estado") or ""),
            str(item.get("fecha") or ""),
            str(item.get("id_receta") or ""),
            str(item.get("id_paciente") or ""),
        ]).lower()
        if ql in hay or (toks and any(tok in hay for tok in toks)):
            filtradas.append(item)
    total = len(filtradas)
    return {"total": total, "recetas": filtradas[offset: offset + limit]}


def resumen_margen() -> dict:
    return margen_agg.listar(limit=100, incluir_inactivos=True)

def seed_basico():
    if not (impuestos.listar(limit=1).get("impuestos") or []):
        impuestos.crear({"nombre": "IVA", "porcentaje": 15, "vigente_desde": "2024-01-01", "activo": True})
    if not (medicamentos.listar(limit=1).get("medicamentos") or []):
        for nombre, pa, pv, pc, libre in [
            ("Insulina NPH", "insulina", 25.0, 12.0, False),
            ("Tiras reactivas", "glucosa", 8.5, 3.0, True),
            ("Metformina 850mg", "metformina", 4.0, 1.2, False),
        ]:
            medicamentos.crear({
                "nombre": nombre, "principio_activo": pa, "forma": "unidad",
                "precio_venta": pv, "precio_costo": pc, "stock_minimo": 10,
                "venta_libre": libre, "activo": True,
            })
