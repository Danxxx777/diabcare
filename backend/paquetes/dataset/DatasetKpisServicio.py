# -*- coding: utf-8 -*-
"""Resumen KPI de módulos hospitalarios (negocio/)."""
from __future__ import annotations


def resumen_kpis() -> dict:
    out = {
        "facturado_total": 0.0,
        "facturas": 0,
        "facturas_pagadas": 0,
        "margen_farmacia": 0.0,
        "ventas_farmacia": 0,
        "urgencias": 0,
        "espera_promedio_min": 0.0,
        "productividad_consultas": 0,
        "ordenes_lab": 0,
        "ordenes_lab_pendientes": 0,
    }
    try:
        from paquetes.facturacion import FacturacionServicio as F
        fac = F.facturas.listar(limit=500, incluir_inactivos=True).get("facturas") or []
        out["facturas"] = len(fac)
        out["facturas_pagadas"] = sum(1 for f in fac if str(f.get("estado") or "").lower() == "pagada")
        out["facturado_total"] = round(sum(float(f.get("total") or 0) for f in fac), 2)
    except Exception:
        pass
    try:
        from paquetes.farmacia import FarmaciaServicio as Farm
        mar = Farm.margen_agg.listar(limit=200, incluir_inactivos=True).get("margenes") or []
        out["margen_farmacia"] = round(sum(float(m.get("margen") or 0) for m in mar), 2)
        ven = Farm.ventas.listar(limit=500, incluir_inactivos=True).get("ventas") or []
        out["ventas_farmacia"] = len(ven)
    except Exception:
        pass
    try:
        from paquetes.urgencias import UrgenciasServicio as U
        urg = U.urgencias.listar(limit=500, incluir_inactivos=True).get("urgencias") or []
        out["urgencias"] = len(urg)
        esp = U.agg_espera.listar(limit=20, incluir_inactivos=True).get("esperas") or []
        if esp:
            out["espera_promedio_min"] = float(esp[0].get("espera_promedio_min") or 0)
    except Exception:
        pass
    try:
        from paquetes.rrhh import RrhhServicio as R
        prod = R.productividad.listar(limit=200, incluir_inactivos=True).get("productividad") or []
        out["productividad_consultas"] = int(sum(int(p.get("num_consultas") or 0) for p in prod))
    except Exception:
        pass
    try:
        from paquetes.laboratorio import LaboratorioServicio as L
        ord_ = L.ordenes.listar(limit=500, incluir_inactivos=True).get("ordenes") or []
        out["ordenes_lab"] = len(ord_)
        out["ordenes_lab_pendientes"] = sum(
            1 for o in ord_ if str(o.get("estado") or "").lower() == "pendiente"
        )
    except Exception:
        pass
    return out
