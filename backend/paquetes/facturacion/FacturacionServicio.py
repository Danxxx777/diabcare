"""P16 Facturación — seguros, tarifario, facturas, pagos."""
from __future__ import annotations
import uuid
from datetime import datetime
from nucleo.utilidades.ParquetStore import ParquetStore

# Sin tope artificial: ParquetStore recorta en memoria tras contar el universo completo.
_SIN_TOPE = 10**9


def _now():
    return datetime.utcnow().isoformat()

seguros = ParquetStore(
    "negocio/dim_seguro.parquet",
    ["id_seguro", "nombre", "cobertura_pct", "activo", "creado_en", "actualizado_en"],
    "id_seguro", "seguros", modo_borrado="activo",
)
tarifario = ParquetStore(
    "negocio/dim_tarifa.parquet",
    ["id_tarifa", "codigo", "descripcion", "precio", "activo", "creado_en", "actualizado_en"],
    "id_tarifa", "tarifas", modo_borrado="activo",
)
facturas = ParquetStore(
    "negocio/hechos_facturacion.parquet",
    ["id_factura", "encounter_id", "id_orden_venta", "id_paciente", "id_seguro",
     "subtotal", "descuento", "iva", "total", "estado", "fecha", "creado_en", "actualizado_en"],
    "id_factura", "facturas", modo_borrado="estado", valor_anulado="anulada",
)
detalle = ParquetStore(
    "negocio/oper_facturas_detalle.parquet",
    ["id_detalle", "id_factura", "concepto", "cantidad", "precio_unitario", "subtotal", "creado_en", "actualizado_en"],
    "id_detalle", "detalles", modo_borrado="estado",
)
pagos = ParquetStore(
    "negocio/oper_pagos.parquet",
    ["id_pago", "id_factura", "monto", "metodo", "fecha", "estado", "creado_en", "actualizado_en"],
    "id_pago", "pagos", modo_borrado="estado",
)
bridge_seguro = ParquetStore(
    "negocio/bridge_paciente_seguro.parquet",
    ["id_bridge", "id_paciente", "id_seguro", "poliza", "activo", "creado_en", "actualizado_en"],
    "id_bridge", "bridges", modo_borrado="activo",
)
agg_costo = ParquetStore(
    "negocio/agg_costo_servicio.parquet",
    ["id_agg", "periodo", "servicio", "costo_total", "facturado_total", "margen", "creado_en", "actualizado_en"],
    "id_agg", "costos", modo_borrado="activo",
)

def crear_factura(datos: dict) -> dict:
    if not datos.get("encounter_id") and not datos.get("id_orden_venta"):
        return {"error": "RN-FACT-001: se requiere encounter_id o id_orden_venta"}
    lineas = datos.pop("lineas", []) or []
    subtotal = float(datos.get("subtotal") or 0)
    if lineas and not subtotal:
        subtotal = sum(float(l.get("cantidad", 1)) * float(l.get("precio_unitario", 0)) for l in lineas)
    descuento = float(datos.get("descuento") or 0)
    id_seguro = datos.get("id_seguro") or ""
    if id_seguro:
        seg = seguros.obtener(str(id_seguro))
        if "error" not in seg:
            max_desc = subtotal * (float(seg.get("cobertura_pct") or 0) / 100.0)
            if descuento > max_desc + 0.01:
                return {"error": "RN-FACT-003: descuento excede cobertura_pct del seguro"}
    iva = float(datos.get("iva") or round(max(subtotal - descuento, 0) * 0.15, 2))
    total = float(datos.get("total") or round(subtotal - descuento + iva, 2))
    res = facturas.crear({
        "encounter_id": str(datos.get("encounter_id") or ""),
        "id_orden_venta": str(datos.get("id_orden_venta") or ""),
        "id_paciente": str(datos.get("id_paciente") or ""),
        "id_seguro": str(id_seguro),
        "subtotal": subtotal, "descuento": descuento, "iva": iva, "total": total,
        "estado": str(datos.get("estado") or "emitida"),
        "fecha": str(datos.get("fecha") or _now()[:10]),
    })
    if res.get("error"):
        return res
    fid = res["id_factura"]
    try:
        from paquetes.notificaciones.NotificacionesServicio import emitir
        from paquetes.clinico.pacientes.PacientesServicio import obtener as obtener_paciente
        email_pac = ""
        pid = str(datos.get("id_paciente") or "")
        if pid:
            p = obtener_paciente(pid)
            if isinstance(p, dict) and not p.get("error"):
                email_pac = str(p.get("email") or "")
        emitir(
            "Factura emitida",
            f"Factura {fid} por ${total:.2f} emitida.",
            "info",
            destinatario_tipo="rol",
            destinatario="administrador",
            canal="in_app",
            referencia_tipo="factura",
            referencia_id=fid,
        )
        if email_pac:
            emitir(
                "Su factura",
                f"Se emitió una factura por ${total:.2f}. Conserve este correo como comprobante.",
                "info",
                destinatario_tipo="paciente_email",
                destinatario=email_pac,
                canal="email",
                destino_email=email_pac,
                referencia_tipo="factura",
                referencia_id=fid,
            )
    except Exception:
        pass
    for ln in lineas:
        cant = float(ln.get("cantidad") or 1)
        pu = float(ln.get("precio_unitario") or 0)
        detalle.crear({
            "id_factura": fid,
            "concepto": str(ln.get("concepto") or "Servicio"),
            "cantidad": cant, "precio_unitario": pu, "subtotal": cant * pu,
        })
    return res

def _enrich_factura(f: dict, pac_map: dict) -> dict:
    pid = str(f.get("id_paciente") or "")
    meta = pac_map.get(pid) or {}
    item = dict(f)
    label_nom = (meta.get("nombre_completo") or "").strip() or "-"
    doc = str(meta.get("documento") or "").strip()
    item["paciente_nombre"] = label_nom
    item["paciente_documento"] = doc
    item["paciente_label"] = f"{label_nom} · {doc}" if doc and label_nom != "-" else label_nom
    item["tiene_foto"] = bool(meta.get("tiene_foto"))
    try:
        item["total"] = float(item.get("total") or 0)
    except (TypeError, ValueError):
        item["total"] = 0.0
    return item


def listar_facturas(offset: int = 0, limit: int = 50, q: str = "") -> dict:
    """Lista facturas enriquecidas. Pagina sobre el universo completo (sin tope 1500)."""
    limit = max(1, min(int(limit or 50), 300))
    offset = max(0, int(offset or 0))
    ql = str(q or "").strip().lower()

    try:
        from nucleo.utilidades.PacientesLookup import mapa_pacientes
    except Exception:
        mapa_pacientes = lambda _ids: {}  # noqa: E731

    if not ql:
        base = facturas.listar(
            offset=offset,
            limit=limit,
            incluir_inactivos=True,
            orden="fecha",
        )
        rows = list(base.get("facturas") or [])
        ids_needed = {str(f.get("id_paciente") or "") for f in rows if f.get("id_paciente")}
        pac_map = mapa_pacientes(ids_needed) if ids_needed else {}
        return {
            "total": int(base.get("total") or 0),
            "facturas": [_enrich_factura(f, pac_map) for f in rows],
        }

    # Búsqueda (incluye nombre/cédula): filtrar universo completo, enriquecer y paginar.
    base = facturas.listar(
        offset=0,
        limit=_SIN_TOPE,
        incluir_inactivos=True,
        orden="fecha",
    )
    rows = list(base.get("facturas") or [])
    ids_needed = {str(f.get("id_paciente") or "") for f in rows if f.get("id_paciente")}
    pac_map = mapa_pacientes(ids_needed) if ids_needed else {}
    enriquecidas = []
    toks = [t for t in ql.replace(",", " ").split() if len(t) >= 2]
    for f in rows:
        item = _enrich_factura(f, pac_map)
        pid = str(item.get("id_paciente") or "")
        hay = " ".join([
            str(item.get("paciente_label") or ""),
            str(item.get("paciente_nombre") or ""),
            str(item.get("paciente_documento") or ""),
            str(item.get("estado") or ""),
            str(item.get("fecha") or ""),
            str(item.get("total") or ""),
            str(item.get("id_factura") or ""),
            pid,
        ]).lower()
        if ql in hay or (toks and any(tok in hay for tok in toks)):
            enriquecidas.append(item)
    total = len(enriquecidas)
    return {"total": total, "facturas": enriquecidas[offset: offset + limit]}


def resumen_caja() -> dict:
    """KPIs sobre el universo completo de facturas (sin tope artificial)."""
    data = facturas.listar(offset=0, limit=_SIN_TOPE, incluir_inactivos=True, orden="fecha")
    rows = data.get("facturas") or []
    emitidas = pagadas = anuladas = 0
    monto_emitido = monto_pagado = monto_pendiente = 0.0
    for f in rows:
        est = str(f.get("estado") or "").lower()
        try:
            total = float(f.get("total") or 0)
        except (TypeError, ValueError):
            total = 0.0
        if est in ("anulada", "anulado"):
            anuladas += 1
            continue
        if est == "pagada":
            pagadas += 1
            monto_pagado += total
        else:
            emitidas += 1
            monto_pendiente += total
        monto_emitido += total
    return {
        "total_facturas": emitidas + pagadas,
        "emitidas": emitidas,
        "pagadas": pagadas,
        "anuladas": anuladas,
        "monto_emitido": round(monto_emitido, 2),
        "monto_pagado": round(monto_pagado, 2),
        "monto_pendiente": round(monto_pendiente, 2),
    }


def seed_basico() -> dict:
    """Catálogo mínimo de seguros y tarifas para demo de caja."""
    creados = {"seguros": 0, "tarifas": 0}
    if not (seguros.listar(limit=1).get("seguros") or []):
        for nombre, pct in [("Particular", 0), ("IESS", 70), ("Seguros Equinoccial", 40)]:
            seguros.crear({"nombre": nombre, "cobertura_pct": pct, "activo": True})
            creados["seguros"] += 1
    if not (tarifario.listar(limit=1).get("tarifas") or []):
        for codigo, desc, precio in [
            ("CONS-DM", "Consulta endocrinología diabetes", 35.0),
            ("LAB-HBA1C", "HbA1c laboratorio", 18.5),
            ("PROC-PIE", "Curación pie diabético", 42.0),
            ("EDU-DM", "Educación diabetológica", 20.0),
        ]:
            tarifario.crear({"codigo": codigo, "descripcion": desc, "precio": precio, "activo": True})
            creados["tarifas"] += 1
    return {"mensaje": "seed facturación ok", **creados}


def listar_pagos_factura(id_factura: str) -> dict:
    return pagos.listar(limit=200, filtros={"id_factura": id_factura}, incluir_inactivos=True)

def crear_pago(id_factura: str, datos: dict) -> dict:
    f = facturas.obtener(id_factura)
    if f.get("error"):
        return f
    pago = pagos.crear({
        "id_factura": id_factura,
        "monto": float(datos.get("monto") or 0),
        "metodo": str(datos.get("metodo") or "efectivo"),
        "fecha": str(datos.get("fecha") or _now()[:10]),
        "estado": str(datos.get("estado") or "registrado"),
    })
    if pago.get("error"):
        return pago
    # Si la suma de pagos cubre el total → factura pagada
    listed = listar_pagos_factura(id_factura)
    acumulado = sum(float(p.get("monto") or 0) for p in (listed.get("pagos") or []))
    total = float(f.get("total") or 0)
    if acumulado + 0.01 >= total and str(f.get("estado") or "").lower() != "anulada":
        facturas.actualizar(id_factura, {"estado": "pagada"})
        pago["factura_estado"] = "pagada"
    else:
        pago["factura_estado"] = f.get("estado")
        pago["saldo"] = round(max(total - acumulado, 0), 2)
    return pago
