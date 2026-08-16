"""P16 Facturación — seguros, tarifario, facturas, pagos."""
from __future__ import annotations
import os
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
    ["id_pago", "id_factura", "monto", "metodo", "referencia", "fecha", "estado", "creado_en", "actualizado_en"],
    "id_pago", "pagos", modo_borrado="estado",
)
enlaces_pago = ParquetStore(
    "negocio/oper_enlaces_pago.parquet",
    ["id_enlace", "token", "id_cita", "id_factura", "monto", "concepto", "paciente",
     "estado", "stripe_session", "creado_en", "actualizado_en"],
    "id_enlace", "enlaces", modo_borrado="estado",
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
    if not lineas:
        # Línea por defecto para comprobante al cliente (consulta / servicio)
        concepto = "Medicamentos / farmacia" if datos.get("id_orden_venta") else "Consulta médica / servicios clínicos"
        monto = subtotal if subtotal > 0 else float(datos.get("total") or 0)
        if monto <= 0:
            monto = 35.0  # tarifa demo consulta
            subtotal = monto
        lineas = [{"concepto": concepto, "cantidad": 1, "precio_unitario": monto}]
        if not datos.get("subtotal"):
            datos["subtotal"] = subtotal
            subtotal = monto
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


def obtener_comprobante(id_factura: str) -> dict:
    """Comprobante / factura para el cliente (consulta, farmacia u otro cobro)."""
    f = facturas.obtener(id_factura)
    if f.get("error"):
        return f
    pac = {"nombre_completo": "-", "documento": "", "email": ""}
    pid = str(f.get("id_paciente") or "")
    if pid:
        try:
            from nucleo.utilidades.PacientesLookup import mapa_pacientes
            pac = (mapa_pacientes({pid}) or {}).get(pid) or pac
        except Exception:
            try:
                from paquetes.clinico.pacientes.PacientesServicio import obtener as obtener_paciente
                p = obtener_paciente(pid)
                if isinstance(p, dict) and not p.get("error"):
                    pac = p
            except Exception:
                pass

    seg_nombre = ""
    sid = str(f.get("id_seguro") or "")
    if sid:
        s = seguros.obtener(sid)
        if not s.get("error"):
            seg_nombre = str(s.get("nombre") or "")

    dets = detalle.listar(limit=200, filtros={"id_factura": id_factura}, incluir_inactivos=True)
    lineas = list(dets.get("detalles") or [])
    if not lineas:
        # Factura sin detalle explícito: una línea genérica para el cliente
        origen = "Medicamentos / farmacia" if f.get("id_orden_venta") else "Consulta / servicios clínicos"
        lineas = [{
            "concepto": origen,
            "cantidad": 1,
            "precio_unitario": float(f.get("subtotal") or f.get("total") or 0),
            "subtotal": float(f.get("subtotal") or f.get("total") or 0),
        }]

    pags = listar_pagos_factura(id_factura).get("pagos") or []
    pagado = sum(float(p.get("monto") or 0) for p in pags)
    total = float(f.get("total") or 0)
    return {
        "id_factura": id_factura,
        "fecha": f.get("fecha") or "",
        "estado": f.get("estado") or "",
        "paciente": {
            "id": pid,
            "nombre": (pac.get("nombre_completo") or pac.get("nombre") or "-"),
            "documento": str(pac.get("documento") or ""),
            "email": str(pac.get("email") or ""),
        },
        "seguro": seg_nombre,
        "subtotal": float(f.get("subtotal") or 0),
        "descuento": float(f.get("descuento") or 0),
        "iva": float(f.get("iva") or 0),
        "total": total,
        "pagado": round(pagado, 2),
        "saldo": round(max(total - pagado, 0), 2),
        "lineas": [{
            "concepto": str(ln.get("concepto") or "Ítem"),
            "cantidad": float(ln.get("cantidad") or 1),
            "precio_unitario": float(ln.get("precio_unitario") or 0),
            "subtotal": float(ln.get("subtotal") or 0),
        } for ln in lineas],
        "pagos": [{
            "fecha": p.get("fecha") or "",
            "metodo": p.get("metodo") or "",
            "monto": float(p.get("monto") or 0),
        } for p in pags],
        "origen": "farmacia" if f.get("id_orden_venta") else "consulta",
    }


def html_comprobante(data: dict) -> str:
    """HTML imprimible del comprobante para el cliente."""
    import html as _html

    def e(v):
        return _html.escape(str(v if v is not None else ""))

    def money(v):
        try:
            return f"${float(v):,.2f}"
        except (TypeError, ValueError):
            return str(v)

    pac = data.get("paciente") or {}
    lineas_html = "".join(
        f"<tr><td>{e(ln['concepto'])}</td>"
        f"<td class='num'>{e(ln['cantidad'])}</td>"
        f"<td class='num'>{money(ln['precio_unitario'])}</td>"
        f"<td class='num'>{money(ln['subtotal'])}</td></tr>"
        for ln in (data.get("lineas") or [])
    )
    pagos_html = "".join(
        f"<tr><td>{e(p['fecha'])}</td><td>{e(p['metodo'])}</td>"
        f"<td class='num'>{money(p['monto'])}</td></tr>"
        for p in (data.get("pagos") or [])
    ) or "<tr><td colspan='3'>Sin pagos registrados aún</td></tr>"
    titulo = "Factura / recibo de farmacia" if data.get("origen") == "farmacia" else "Factura / recibo de consulta"
    return f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8">
<title>Comprobante {e(data.get('id_factura'))}</title>
<style>
  @page {{ size: A4; margin: 14mm; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; color: #0f172a; margin: 0; padding: 24px; }}
  .sheet {{ max-width: 720px; margin: 0 auto; }}
  .head {{ display:flex; justify-content:space-between; gap:16px; border-bottom:3px solid #1d4ed8; padding-bottom:12px; }}
  .brand {{ font-size:22px; font-weight:800; color:#1e3a8a; }}
  .meta {{ text-align:right; font-size:12px; color:#475569; }}
  h1 {{ font-size:18px; margin:18px 0 6px; }}
  .box {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px 14px; margin:12px 0; font-size:13px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:10px; font-size:13px; }}
  th {{ text-align:left; background:#eff6ff; color:#1e3a8a; padding:8px; border-bottom:1px solid #bfdbfe; }}
  td {{ padding:8px; border-bottom:1px solid #e2e8f0; }}
  .num {{ text-align:right; font-variant-numeric: tabular-nums; }}
  .tot {{ margin-top:14px; width:280px; margin-left:auto; font-size:13px; }}
  .tot div {{ display:flex; justify-content:space-between; padding:4px 0; }}
  .tot .grand {{ font-weight:800; font-size:16px; border-top:2px solid #1d4ed8; margin-top:6px; padding-top:8px; }}
  .foot {{ margin-top:28px; font-size:11px; color:#64748b; text-align:center; }}
  .actions {{ margin:16px 0; text-align:right; }}
  .actions button {{ background:#1d4ed8; color:#fff; border:0; border-radius:8px; padding:8px 14px; cursor:pointer; font-weight:700; }}
  @media print {{ .actions {{ display:none; }} body {{ padding:0; }} }}
</style>
</head><body>
<div class="sheet">
  <div class="actions"><button onclick="window.print()">Imprimir / guardar PDF</button></div>
  <div class="head">
    <div>
      <div class="brand">DiabCare Hospital</div>
      <div style="font-size:12px;color:#64748b">Comprobante para el cliente</div>
    </div>
    <div class="meta">
      <div><strong>{e(titulo)}</strong></div>
      <div>N.º {e(data.get('id_factura'))}</div>
      <div>Fecha: {e(data.get('fecha'))}</div>
      <div>Estado: {e(data.get('estado'))}</div>
    </div>
  </div>
  <h1>Datos del paciente</h1>
  <div class="box">
    <div><strong>{e(pac.get('nombre'))}</strong></div>
    <div>Documento: {e(pac.get('documento') or '—')}</div>
    <div>Seguro: {e(data.get('seguro') or 'Particular / sin seguro')}</div>
  </div>
  <h1>Detalle</h1>
  <table>
    <thead><tr><th>Concepto</th><th class="num">Cant.</th><th class="num">P. unit.</th><th class="num">Subtotal</th></tr></thead>
    <tbody>{lineas_html}</tbody>
  </table>
  <div class="tot">
    <div><span>Subtotal</span><span>{money(data.get('subtotal'))}</span></div>
    <div><span>Descuento</span><span>{money(data.get('descuento'))}</span></div>
    <div><span>IVA</span><span>{money(data.get('iva'))}</span></div>
    <div class="grand"><span>Total</span><span>{money(data.get('total'))}</span></div>
    <div><span>Pagado</span><span>{money(data.get('pagado'))}</span></div>
    <div><span>Saldo</span><span>{money(data.get('saldo'))}</span></div>
  </div>
  <h1>Pagos</h1>
  <table>
    <thead><tr><th>Fecha</th><th>Método</th><th class="num">Monto</th></tr></thead>
    <tbody>{pagos_html}</tbody>
  </table>
  <div class="foot">
    Documento generado por DiabCare · informe simple de caja para el cliente.<br>
    Conserve este comprobante. No incluye historia clínica ni datos sensibles.
  </div>
</div>
</body></html>"""


def crear_pago(id_factura: str, datos: dict) -> dict:
    f = facturas.obtener(id_factura)
    if f.get("error"):
        return f
    pago = pagos.crear({
        "id_factura": id_factura,
        "monto": float(datos.get("monto") or 0),
        "metodo": str(datos.get("metodo") or "efectivo"),
        "referencia": str(datos.get("referencia") or ""),
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
        _marcar_enlaces_pagados(id_factura)
        _confirmar_cita_de_factura(f)
    else:
        pago["factura_estado"] = f.get("estado")
        pago["saldo"] = round(max(total - acumulado, 0), 2)
    return pago


def _stripe_secret() -> str:
    env = (os.getenv("STRIPE_SECRET_KEY") or os.getenv("DIABCARE_STRIPE_SECRET") or "").strip()
    if env:
        return env
    try:
        from paquetes.configuracion.ConfiguracionServicio import obtener_configuracion
        cfg = obtener_configuracion(enmascarar_secretos=False)
        return str(cfg.get("stripe_secret_key") or "").strip()
    except Exception:
        return ""


def stripe_disponible() -> bool:
    k = _stripe_secret()
    return k.startswith("sk_")


def _qr_png_b64(url: str) -> str:
    try:
        import base64
        import io
        import qrcode
        qr = qrcode.QRCode(version=4, box_size=6, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


def _enlace_por_token(token: str) -> dict | None:
    tok = str(token or "").strip()
    if not tok:
        return None
    rows = enlaces_pago.listar(limit=_SIN_TOPE, incluir_inactivos=True).get("enlaces") or []
    for e in rows:
        if str(e.get("token") or "") == tok:
            return e
    return None


def _marcar_enlaces_pagados(id_factura: str) -> None:
    fid = str(id_factura or "")
    rows = enlaces_pago.listar(limit=_SIN_TOPE, incluir_inactivos=True).get("enlaces") or []
    for e in rows:
        if str(e.get("id_factura") or "") == fid and str(e.get("estado") or "") != "pagado":
            enlaces_pago.actualizar(e.get("id_enlace"), {"estado": "pagado"})


def _confirmar_cita_de_factura(fac: dict) -> None:
    cid = str((fac or {}).get("encounter_id") or "")
    if not cid:
        return
    try:
        from paquetes.clinico.citas.CitasServicio import actualizar, obtener
        cita = obtener(cid)
        if cita.get("error"):
            return
        est = str(cita.get("estado") or "").lower()
        if est == "programada":
            actualizar(cid, {"estado": "confirmada"})
    except Exception:
        pass


def factura_abierta_por_cita(id_cita: str) -> dict | None:
    cid = str(id_cita or "").strip()
    if not cid:
        return None
    rows = facturas.listar(offset=0, limit=_SIN_TOPE, incluir_inactivos=True).get("facturas") or []
    for f in rows:
        if str(f.get("encounter_id") or "") != cid:
            continue
        if str(f.get("estado") or "").lower() in ("pagada", "anulada"):
            continue
        return f
    return None


def concepto_factura(id_factura: str) -> str:
    fid = str(id_factura or "")
    rows = detalle.listar(offset=0, limit=_SIN_TOPE, incluir_inactivos=True).get("detalles") or []
    for d in rows:
        if str(d.get("id_factura") or "") == fid:
            return str(d.get("concepto") or "Consulta médica")
    return "Consulta médica"


def crear_enlace_pago(id_factura: str, id_cita: str = "", concepto: str = "", paciente: str = "") -> dict:
    f = facturas.obtener(id_factura)
    if f.get("error"):
        return f
    if str(f.get("estado") or "").lower() == "pagada":
        return {"error": "La factura ya está pagada"}
    from nucleo.utilidades.UrlPublica import alcance_url
    alcance = alcance_url()
    monto = round(float(f.get("total") or 0), 2)
    concepto_n = concepto or "Consulta médica"
    rows = enlaces_pago.listar(limit=_SIN_TOPE, incluir_inactivos=True).get("enlaces") or []
    existente = next(
        (e for e in rows
         if str(e.get("id_factura") or "") == str(id_factura)
         and str(e.get("estado") or "") == "pendiente"
         and str(e.get("token") or "")),
        None,
    )
    if existente:
        token = str(existente.get("token"))
        url = f"{alcance['url']}/p/{token}"
        return {
            "token": token,
            "url": url,
            "qr_png": _qr_png_b64(url),
            "monto": monto,
            "concepto": existente.get("concepto") or concepto_n,
            "alcance": alcance["alcance"],
            "internet": alcance["internet"],
            "stripe": stripe_disponible(),
            "id_factura": id_factura,
            "id_enlace": existente.get("id_enlace"),
        }
    token = uuid.uuid4().hex[:10]
    url = f"{alcance['url']}/p/{token}"
    res = enlaces_pago.crear({
        "token": token,
        "id_cita": str(id_cita or f.get("encounter_id") or ""),
        "id_factura": str(id_factura),
        "monto": monto,
        "concepto": concepto_n,
        "paciente": paciente,
        "estado": "pendiente",
        "stripe_session": "",
    })
    if res.get("error"):
        return res
    return {
        "token": token,
        "url": url,
        "qr_png": _qr_png_b64(url),
        "monto": monto,
        "concepto": concepto_n,
        "alcance": alcance["alcance"],
        "internet": alcance["internet"],
        "stripe": stripe_disponible(),
        "id_factura": id_factura,
        "id_enlace": res.get("id_enlace"),
    }


def publico_pago(token: str) -> dict:
    e = _enlace_por_token(token)
    if not e:
        return {"error": "Enlace no válido o vencido"}
    f = facturas.obtener(str(e.get("id_factura") or ""))
    pagada = (not f.get("error")) and str(f.get("estado") or "").lower() == "pagada"
    estado = "pagado" if pagada else str(e.get("estado") or "pendiente")
    if pagada and str(e.get("estado") or "") != "pagado":
        enlaces_pago.actualizar(e.get("id_enlace"), {"estado": "pagado"})
    nom = str(e.get("paciente") or "Paciente").strip().split()
    visible = nom[0] if nom else "Paciente"
    return {
        "token": token,
        "estado": estado,
        "monto": float(e.get("monto") or 0),
        "concepto": e.get("concepto") or "Consulta médica",
        "paciente": visible,
        "stripe": stripe_disponible() and estado != "pagado",
        "pagado": estado == "pagado",
    }


def iniciar_checkout_stripe(token: str) -> dict:
    info = publico_pago(token)
    if info.get("error"):
        return info
    if info.get("pagado"):
        return {"error": "Este cobro ya está pagado"}
    secret = _stripe_secret()
    if not secret.startswith("sk_"):
        return {"error": "Stripe no está configurado. En caja puede cobrar en efectivo o guardar la clave de prueba en Configuración."}
    e = _enlace_por_token(token)
    from nucleo.utilidades.UrlPublica import base_publica
    base = base_publica()
    try:
        import stripe
        stripe.api_key = secret
        session = stripe.checkout.Session.create(
            mode="payment",
            client_reference_id=token,
            success_url=f"{base}/p/{token}?ok=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}/p/{token}?cancel=1",
            line_items=[{
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(round(float(info["monto"]) * 100)),
                    "product_data": {
                        "name": str(info.get("concepto") or "Consulta DiabCare"),
                    },
                },
            }],
        )
        enlaces_pago.actualizar(e.get("id_enlace"), {"stripe_session": session.id})
        return {"url": session.url, "session_id": session.id}
    except Exception as exc:
        return {"error": f"Stripe: {exc}"}


def confirmar_checkout_stripe(token: str, session_id: str) -> dict:
    info = publico_pago(token)
    if info.get("error"):
        return info
    if info.get("pagado"):
        return info
    secret = _stripe_secret()
    if not secret.startswith("sk_"):
        return {"error": "Stripe no está configurado"}
    try:
        import stripe
        stripe.api_key = secret
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        return {"error": f"No se pudo verificar el pago: {exc}"}
    paid = str(getattr(session, "payment_status", "") or "").lower() == "paid"
    ref = str(getattr(session, "client_reference_id", "") or "")
    if not paid or ref != token:
        return {"error": "El pago no consta como completado en Stripe"}
    e = _enlace_por_token(token)
    pago = crear_pago(str(e.get("id_factura")), {
        "monto": float(e.get("monto") or 0),
        "metodo": "tarjeta",
        "referencia": session_id[:24],
        "fecha": _now()[:10],
    })
    if pago.get("error"):
        return pago
    return publico_pago(token)
