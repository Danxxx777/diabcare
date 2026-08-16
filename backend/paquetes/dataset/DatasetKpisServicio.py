# -*- coding: utf-8 -*-
"""Resumen KPI de módulos hospitalarios (negocio/)."""
from __future__ import annotations

import time
from typing import Any

_MEMO: dict[str, tuple[float, Any]] = {}
_MEMO_TTL = 45.0


def _memo_get(key: str):
    hit = _MEMO.get(key)
    if hit and (time.monotonic() - hit[0]) < _MEMO_TTL:
        return hit[1]
    return None


def _memo_set(key: str, val: Any) -> Any:
    _MEMO[key] = (time.monotonic(), val)
    return val


def invalidar_memo_kpis() -> None:
    _MEMO.clear()


def resumen_kpis() -> dict:
    cached = _memo_get("resumen_kpis")
    if cached is not None:
        return cached

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
        df = F.facturas.extraer()
        if not df.empty:
            out["facturas"] = int(len(df))
            if "estado" in df.columns:
                est = df["estado"].astype(str).str.lower()
                out["facturas_pagadas"] = int(est.eq("pagada").sum())
            if "total" in df.columns:
                out["facturado_total"] = round(float(df["total"].fillna(0).astype(float).sum()), 2)
    except Exception:
        pass
    try:
        from paquetes.farmacia import FarmaciaServicio as Farm
        mar = Farm.margen_agg.extraer()
        if not mar.empty and "margen" in mar.columns:
            out["margen_farmacia"] = round(float(mar["margen"].fillna(0).astype(float).sum()), 2)
        ven = Farm.ventas.extraer()
        out["ventas_farmacia"] = int(len(ven)) if not ven.empty else 0
    except Exception:
        pass
    try:
        from paquetes.urgencias import UrgenciasServicio as U
        urg = U.urgencias.extraer()
        out["urgencias"] = int(len(urg)) if not urg.empty else 0
        esp = U.agg_espera.extraer()
        if not esp.empty and "espera_promedio_min" in esp.columns:
            out["espera_promedio_min"] = float(esp.iloc[0].get("espera_promedio_min") or 0)
    except Exception:
        pass
    try:
        from paquetes.rrhh import RrhhServicio as R
        prod = R.productividad.extraer()
        if not prod.empty and "num_consultas" in prod.columns:
            out["productividad_consultas"] = int(prod["num_consultas"].fillna(0).astype(float).sum())
    except Exception:
        pass
    try:
        from paquetes.laboratorio import LaboratorioServicio as L
        ord_ = L.ordenes.extraer()
        if not ord_.empty:
            out["ordenes_lab"] = int(len(ord_))
            if "estado" in ord_.columns:
                out["ordenes_lab_pendientes"] = int(
                    ord_["estado"].astype(str).str.lower().eq("pendiente").sum()
                )
    except Exception:
        pass
    return _memo_set("resumen_kpis", out)


def informes_complejos() -> dict:
    """Informes compuestos: agregaciones materializadas (negocio/agg_*)."""
    cached = _memo_get("informes_complejos")
    if cached is not None:
        return cached

    out = {
        "productividad_medica": [],
        "margen_farmacia": [],
        "medicamentos_top": [],
        "espera_urgencias": [],
        "costo_servicio": [],
        "ingresos_por_dia": [],
    }

    try:
        from paquetes.rrhh import RrhhServicio as R
        df = R.productividad.extraer()
        if not df.empty:
            work = df.copy()
            if "ingreso_generado" in work.columns:
                work["_ord"] = work["ingreso_generado"].fillna(0).astype(float)
                work = work.sort_values("_ord", ascending=False)
            rows = work.head(15).fillna("")
            out["productividad_medica"] = [{
                "id_personal": r.get("id_personal"),
                "periodo": r.get("periodo"),
                "num_consultas": int(r.get("num_consultas") or 0),
                "num_procedimientos": int(r.get("num_procedimientos") or 0),
                "ingreso_generado": round(float(r.get("ingreso_generado") or 0), 2),
            } for r in rows.to_dict(orient="records")]
    except Exception:
        pass

    try:
        from paquetes.farmacia import FarmaciaServicio as Farm
        meds = Farm.medicamentos.extraer()
        nombres = {}
        if not meds.empty and "id_medicamento" in meds.columns:
            for r in meds.fillna("").to_dict(orient="records"):
                nombres[str(r.get("id_medicamento"))] = str(r.get("nombre") or "")
        df = Farm.margen_agg.extraer()
        if not df.empty:
            work = df.copy()
            if "margen" in work.columns:
                work["_ord"] = work["margen"].fillna(0).astype(float)
                work = work.sort_values("_ord", ascending=False)
            rows = work.head(15).fillna("")
            out["margen_farmacia"] = [{
                "medicamento": nombres.get(str(r.get("id_medicamento")), str(r.get("id_medicamento") or "")),
                "periodo": r.get("periodo"),
                "ingreso_total": round(float(r.get("ingreso_total") or 0), 2),
                "costo_total": round(float(r.get("costo_total") or 0), 2),
                "margen": round(float(r.get("margen") or 0), 2),
            } for r in rows.to_dict(orient="records")]
    except Exception:
        pass

    try:
        from nucleo.utilidades.ParquetStore import ParquetStore
        top_store = ParquetStore(
            "negocio/agg_medicamentos_top.parquet",
            ["id_agg", "id_medicamento", "nombre", "total_dispensaciones", "periodo",
             "creado_en", "actualizado_en"],
            "id_agg", "tops", modo_borrado="activo",
        )
        df = top_store.extraer()
        if not df.empty:
            work = df.copy()
            if "total_dispensaciones" in work.columns:
                work["_ord"] = work["total_dispensaciones"].fillna(0).astype(float)
                work = work.sort_values("_ord", ascending=False)
            rows = work.head(10).fillna("")
            out["medicamentos_top"] = [{
                "nombre": r.get("nombre"),
                "total_dispensaciones": int(r.get("total_dispensaciones") or 0),
                "periodo": r.get("periodo"),
            } for r in rows.to_dict(orient="records")]
    except Exception:
        pass

    try:
        from paquetes.urgencias import UrgenciasServicio as U
        df = U.agg_espera.extraer()
        if not df.empty:
            out["espera_urgencias"] = [{
                "periodo": r.get("periodo"),
                "espera_promedio_min": round(float(r.get("espera_promedio_min") or 0), 1),
                "total_urgencias": int(r.get("total_urgencias") or 0),
            } for r in df.fillna("").to_dict(orient="records")]
    except Exception:
        pass

    try:
        from paquetes.facturacion import FacturacionServicio as F
        df = F.agg_costo.extraer()
        if not df.empty:
            work = df.copy()
            if "facturado_total" in work.columns:
                work["_ord"] = work["facturado_total"].fillna(0).astype(float)
                work = work.sort_values("_ord", ascending=False)
            rows = work.head(15).fillna("")
            out["costo_servicio"] = [{
                "servicio": r.get("servicio"),
                "periodo": r.get("periodo"),
                "costo_total": round(float(r.get("costo_total") or 0), 2),
                "facturado_total": round(float(r.get("facturado_total") or 0), 2),
                "margen": round(float(r.get("margen") or 0), 2),
            } for r in rows.to_dict(orient="records")]
    except Exception:
        pass

    try:
        from paquetes.facturacion import FacturacionServicio as F
        df = F.facturas.extraer()
        if not df.empty and "fecha" in df.columns:
            work = df.copy()
            if "estado" in work.columns:
                est = work["estado"].astype(str).str.lower()
                work = work[~est.isin(["anulada", "anulado"])]
            work["fecha_d"] = work["fecha"].astype(str).str[:10]
            work = work[work["fecha_d"].str.len() == 10]
            work["total_n"] = work["total"].fillna(0).astype(float) if "total" in work.columns else 0.0
            g = work.groupby("fecha_d", as_index=False).agg(total=("total_n", "sum"), facturas=("fecha_d", "count"))
            g = g.sort_values("fecha_d").tail(30)
            out["ingresos_por_dia"] = [
                {"fecha": r["fecha_d"], "total": round(float(r["total"]), 2), "facturas": int(r["facturas"])}
                for r in g.to_dict(orient="records")
            ]
    except Exception:
        pass

    return _memo_set("informes_complejos", out)
