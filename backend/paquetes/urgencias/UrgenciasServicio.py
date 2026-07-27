"""P19 Urgencias."""
from __future__ import annotations
from datetime import datetime
from nucleo.utilidades.ParquetStore import ParquetStore
from nucleo.utilidades.PacientesLookup import mapa_pacientes

TRIAGE_LABEL = {
    "I": "I · Crítico (inmediato)",
    "II": "II · Emergencia",
    "III": "III · Urgente",
    "IV": "IV · Menos urgente",
    "V": "V · No urgente",
}
ESTADOS_LABEL = {
    "triage": "En triage",
    "en_espera": "En espera",
    "registrado": "Registrado",
    "atendida": "Atendida",
    "anulado": "Anulado",
    "anulada": "Anulada",
}
DESENLACES_LABEL = {
    "en_espera": "En espera",
    "alta": "Alta",
    "hospitalizacion": "Hospitalización",
    "referencia": "Referencia",
}


def _now():
    return datetime.utcnow().isoformat()


urgencias = ParquetStore(
    "negocio/hechos_emergencia.parquet",
    ["id_urgencia", "id_paciente", "triage", "motivo", "id_enfermero", "id_medico",
     "hora_llegada", "hora_atencion", "desenlace", "estado", "creado_en", "actualizado_en"],
    "id_urgencia", "urgencias", modo_borrado="estado",
)
agg_espera = ParquetStore(
    "negocio/agg_tiempos_espera.parquet",
    ["id_agg", "periodo", "espera_promedio_min", "total_urgencias", "creado_en", "actualizado_en"],
    "id_agg", "esperas", modo_borrado="activo",
)


def enriquecer(filas: list) -> list:
    if not filas:
        return []
    ids = {str(r.get("id_paciente") or "") for r in filas}
    mapa = mapa_pacientes(ids)
    out = []
    for r in filas:
        x = dict(r)
        pid = str(x.get("id_paciente") or "").strip()
        p = mapa.get(pid) or {}
        nombre = (p.get("nombre_completo") or "").strip()
        doc = str(p.get("documento") or "").strip()
        x["paciente_nombre"] = nombre or (f"Paciente {pid[:8]}…" if pid else "—")
        x["documento"] = doc
        x["paciente_label"] = x["paciente_nombre"]
        x["tiene_foto"] = bool(p.get("tiene_foto"))

        tri = str(x.get("triage") or "").strip().upper()
        x["triage_label"] = TRIAGE_LABEL.get(tri, tri or "—")
        est = str(x.get("estado") or "").strip().lower()
        x["estado_label"] = ESTADOS_LABEL.get(est, (est[:1].upper() + est[1:]) if est else "—")
        des = str(x.get("desenlace") or "").strip().lower()
        x["desenlace_label"] = DESENLACES_LABEL.get(des, des.replace("_", " ").title() if des else "—")
        out.append(x)
    return out


def listar_enriquecido(**kwargs) -> dict:
    res = urgencias.listar(**kwargs)
    res["urgencias"] = enriquecer(res.get("urgencias") or [])
    return res


def crear_triage(datos: dict, id_enfermero: str) -> dict:
    return urgencias.crear({
        "id_paciente": str(datos.get("id_paciente") or ""),
        "triage": str(datos.get("triage") or "III").upper(),
        "motivo": str(datos.get("motivo") or ""),
        "id_enfermero": id_enfermero,
        "id_medico": "",
        "hora_llegada": str(datos.get("hora_llegada") or _now()),
        "hora_atencion": "",
        "desenlace": "en_espera",
        "estado": "triage",
    })


def atender(id_urgencia: str, id_medico: str, datos: dict | None = None) -> dict:
    u = urgencias.obtener(id_urgencia)
    if u.get("error"):
        return u
    desenlace = str((datos or {}).get("desenlace") or "alta").lower().strip()
    if desenlace not in DESENLACES_LABEL or desenlace == "en_espera":
        return {"error": "Indique el desenlace: alta, hospitalizacion o referencia"}
    cambios = {
        "id_medico": id_medico,
        "hora_atencion": _now(),
        "estado": "atendida",
        "desenlace": desenlace,
    }
    return urgencias.actualizar(id_urgencia, cambios)
