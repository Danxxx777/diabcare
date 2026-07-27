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


def listar_ordenes(**kwargs) -> dict:
    res = ordenes.listar(**kwargs)
    res["ordenes"] = enriquecer(res.get("ordenes") or [], estados=ESTADOS_ORDEN)
    return res


def listar_resultados(**kwargs) -> dict:
    res = resultados.listar(**kwargs)
    res["resultados"] = enriquecer(res.get("resultados") or [], estados=ESTADOS_RESULTADO)
    return res


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
        nombre = str(pr.get("nombre") or pr.get("codigo") or "").lower()
        if "hba1c" in nombre or "glucosa" in nombre:
            from paquetes.notificaciones.NotificacionesServicio import crear as notif_crear
            pac = str(o.get("id_paciente") or "")
            notif_crear({
                "titulo": "Resultado lab clínico",
                "mensaje": f"{nombre}: {valor} {unidad} (paciente {pac})",
                "tipo": "info",
            })
    except Exception:
        pass
    return r


def seed():
    if not (pruebas.listar(limit=1).get("pruebas") or []):
        for codigo, nombre, unidad in [
            ("HBA1C", "HbA1c", "%"),
            ("GLU", "Glucosa en ayunas", "mg/dL"),
            ("CREA", "Creatinina", "mg/dL"),
            ("LIP", "Perfil lipídico", "mg/dL"),
        ]:
            pruebas.crear({"codigo": codigo, "nombre": nombre, "unidad": unidad, "activo": True})
