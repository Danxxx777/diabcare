"""P18 Laboratorio."""
from __future__ import annotations
from datetime import datetime
from nucleo.utilidades.ParquetStore import ParquetStore
from nucleo.utilidades.PacientesLookup import mapa_pacientes

ESTADOS_ORDEN = {
    "pendiente": "Pendiente",
    "completada": "Completada",
    "anulada": "Anulada",
    "anulado": "Anulada",
}
ESTADOS_RESULTADO = {
    "registrado": "Registrado",
    "activa": "Activo",
    "activo": "Activo",
    "anulado": "Anulado",
    "anulada": "Anulada",
}


def _now():
    return datetime.utcnow().isoformat()


pruebas = ParquetStore(
    "negocio/dim_laboratorio_prueba.parquet",
    ["id_prueba", "codigo", "nombre", "unidad", "activo", "creado_en", "actualizado_en"],
    "id_prueba", "pruebas", modo_borrado="activo",
)
ordenes = ParquetStore(
    "negocio/oper_ordenes_lab.parquet",
    ["id_orden", "id_paciente", "id_prueba", "id_medico", "encounter_id", "estado",
     "fecha", "creado_en", "actualizado_en"],
    "id_orden", "ordenes", modo_borrado="estado", valor_anulado="anulada",
)
resultados = ParquetStore(
    "negocio/hechos_laboratorio.parquet",
    ["id_resultado", "id_orden", "id_paciente", "id_prueba", "valor", "unidad",
     "fecha", "estado", "creado_en", "actualizado_en"],
    "id_resultado", "resultados", modo_borrado="estado",
)


def _mapa_pruebas(ids: set[str] | None = None) -> dict:
    try:
        res = pruebas.listar(limit=10**9, incluir_inactivos=True)
        out = {str(p.get("id_prueba") or ""): p for p in (res.get("pruebas") or [])}
        if ids:
            return {k: v for k, v in out.items() if k in ids}
        return out
    except Exception:
        return {}


def enriquecer(filas: list, *, estados: dict | None = None) -> list:
    if not filas:
        return []
    ids_p = {str(r.get("id_paciente") or "") for r in filas}
    ids_pr = {str(r.get("id_prueba") or "") for r in filas}
    mapa_p = mapa_pacientes(ids_p)
    mapa_pr = _mapa_pruebas(ids_pr)
    est_map = estados or ESTADOS_ORDEN
    out = []
    for r in filas:
        x = dict(r)
        pid = str(x.get("id_paciente") or "")
        prid = str(x.get("id_prueba") or "")
        p = mapa_p.get(pid) or {}
        pr = mapa_pr.get(prid) or {}

        nombre = (p.get("nombre_completo") or "").strip()
        doc = str(p.get("documento") or "").strip()
        x["paciente_nombre"] = nombre or (f"Paciente {pid[:8]}…" if pid else "—")
        x["documento"] = doc
        x["paciente_label"] = x["paciente_nombre"]
        x["tiene_foto"] = bool(p.get("tiene_foto"))

        pnombre = str(pr.get("nombre") or pr.get("codigo") or "").strip()
        punidad = str(pr.get("unidad") or "").strip()
        x["prueba_nombre"] = pnombre
        x["prueba_unidad"] = punidad or str(x.get("unidad") or "")
        if pnombre and punidad:
            x["prueba_label"] = f"{pnombre} ({punidad})"
        else:
            x["prueba_label"] = pnombre or "—"

        est = str(x.get("estado") or "").lower()
        x["estado_label"] = est_map.get(est, (est[:1].upper() + est[1:]) if est else "—")
        out.append(x)
    return out


_CAMPOS_BUSQUEDA = (
    "paciente_nombre", "paciente_label", "documento", "prueba_label",
    "prueba_nombre", "estado", "estado_label", "valor", "unidad", "fecha",
)


def _filtrar_enriquecidos(rows: list, q: str) -> list:
    ql = str(q or "").strip().lower()
    if not ql:
        return rows
    tokens = [t for t in ql.replace(",", " ").split() if t]
    out = []
    for r in rows:
        blob = " ".join(str(r.get(k) or "") for k in _CAMPOS_BUSQUEDA).lower()
        if ql in blob or (tokens and all(t in blob for t in tokens)):
            out.append(r)
    return out


def _listar_enriquecido(store, key: str, estados: dict, offset: int = 0, limit: int = 50, q: str = "", **kwargs) -> dict:
    """Lista + enriquece; con q busca por nombre/cédula/prueba (no por UUID)."""
    incluir = kwargs.get("incluir_inactivos", True)
    qn = str(q or "").strip()
    if qn:
        res = store.listar(offset=0, limit=10**9, q="", incluir_inactivos=incluir)
        rows = enriquecer(res.get(key) or [], estados=estados)
        rows = _filtrar_enriquecidos(rows, qn)
        total = len(rows)
        return {"total": total, key: rows[offset: offset + limit]}
    res = store.listar(offset=offset, limit=limit, q="", incluir_inactivos=incluir)
    res[key] = enriquecer(res.get(key) or [], estados=estados)
    return res


def listar_ordenes(**kwargs) -> dict:
    return _listar_enriquecido(ordenes, "ordenes", ESTADOS_ORDEN, **kwargs)


def listar_resultados(**kwargs) -> dict:
    return _listar_enriquecido(resultados, "resultados", ESTADOS_RESULTADO, **kwargs)


def cargar_resultado(id_orden: str, datos: dict) -> dict:
    o = ordenes.obtener(id_orden)
    if o.get("error"):
        return o
    valor = str(datos.get("valor") or "").strip()
    if not valor:
        return {"error": "Indique el valor del resultado"}
    pr = pruebas.obtener(str(o.get("id_prueba") or ""))
    if pr.get("error"):
        pr = {}
    unidad = str(datos.get("unidad") or pr.get("unidad") or "").strip()
    r = resultados.crear({
        "id_orden": id_orden,
        "id_paciente": o.get("id_paciente") or "",
        "id_prueba": o.get("id_prueba") or "",
        "valor": valor, "unidad": unidad,
        "fecha": str(datos.get("fecha") or _now()[:10]),
        "estado": "registrado",
    })
    ordenes.actualizar(id_orden, {"estado": "completada"})
    try:
        from paquetes.notificaciones.NotificacionesServicio import emitir_a_roles
        nombre = str(pr.get("nombre") or pr.get("codigo") or "Prueba")
        pac = str(o.get("id_paciente") or "")
        emitir_a_roles(
            "Resultado de laboratorio listo",
            f"{nombre}: {valor} {unidad} (paciente {pac}). Revise en Laboratorio / expediente.",
            "info",
            roles=["medico"],
            referencia_tipo="lab_orden",
            referencia_id=str(id_orden),
        )
    except Exception:
        pass
    return r


def resumen_operativo() -> dict:
    """Informe simple: órdenes pendientes vs completadas y resultados cargados."""
    odf = ordenes.extraer(copiar=False)
    rdf = resultados.extraer(copiar=False)
    pdf_ = pruebas.extraer(copiar=False)
    pend = comp = anul = 0
    if not odf.empty and "estado" in odf.columns:
        est = odf["estado"].astype(str).str.lower()
        pend = int(est.eq("pendiente").sum())
        comp = int(est.eq("completada").sum())
        anul = int(est.isin(["anulada", "anulado"]).sum())
    return {
        "tipo": "informe_simple",
        "ordenes_total": int(len(odf)),
        "ordenes_pendientes": pend,
        "ordenes_completadas": comp,
        "ordenes_anuladas": anul,
        "resultados_registrados": int(len(rdf)),
        "pruebas_catalogo": int(len(pdf_)),
    }


def seed():
    if not (pruebas.listar(limit=1).get("pruebas") or []):
        for codigo, nombre, unidad in [
            ("HBA1C", "HbA1c", "%"),
            ("GLU", "Glucosa en ayunas", "mg/dL"),
            ("CREA", "Creatinina", "mg/dL"),
            ("LIP", "Perfil lipídico", "mg/dL"),
        ]:
            pruebas.crear({"codigo": codigo, "nombre": nombre, "unidad": unidad, "activo": True})
