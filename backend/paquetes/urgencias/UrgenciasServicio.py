"""P19 Urgencias."""
from __future__ import annotations
from datetime import datetime
from nucleo.utilidades.ParquetStore import ParquetStore
from nucleo.utilidades.PacientesLookup import mapa_pacientes
from nucleo.modelos.catalogo.ViasLlegada import VIAS_LLEGADA

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
    ["id_urgencia", "id_paciente", "triage", "motivo", "via_llegada", "id_enfermero", "id_medico",
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
        x["via_llegada_label"] = VIAS_LLEGADA.get(str(x.get("via_llegada") or "").lower(), "—")
        out.append(x)
    return out


def listar_enriquecido(**kwargs) -> dict:
    q = str(kwargs.pop("q", "") or "").strip()
    offset = int(kwargs.get("offset") or 0)
    limit = int(kwargs.get("limit") or 50)
    if q:
        kwargs = {**kwargs, "offset": 0, "limit": 10**9, "q": ""}
        res = urgencias.listar(**kwargs)
        rows = enriquecer(res.get("urgencias") or [])
        ql = q.lower()
        tokens = [t for t in ql.replace(",", " ").split() if t]
        campos = ("paciente_nombre", "documento", "motivo", "triage", "triage_label", "estado", "estado_label", "via_llegada")
        filtradas = []
        for r in rows:
            blob = " ".join(str(r.get(k) or "") for k in campos).lower()
            if ql in blob or (tokens and all(t in blob for t in tokens)):
                filtradas.append(r)
        return {"total": len(filtradas), "urgencias": filtradas[offset: offset + limit]}
    res = urgencias.listar(**kwargs)
    res["urgencias"] = enriquecer(res.get("urgencias") or [])
    return res


def crear_triage(datos: dict, id_enfermero: str) -> dict:
    via = str(datos.get("via_llegada") or "propia").lower()
    if via not in VIAS_LLEGADA:
        return {"error": "Seleccione una vía de llegada válida"}
    if not str(datos.get("id_paciente") or "").strip():
        return {"error": "Seleccione el paciente antes de registrar el triage"}
    if not str(datos.get("motivo") or "").strip():
        return {"error": "Indique el motivo de la urgencia"}
    return urgencias.crear({
        "id_paciente": str(datos.get("id_paciente") or ""),
        "triage": str(datos.get("triage") or "III").upper(),
        "motivo": str(datos.get("motivo") or ""),
        "via_llegada": via,
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


def resumen_operativo() -> dict:
    """Informe simple: cola de urgencias por estado y triage."""
    df = urgencias.extraer(copiar=False)
    if df.empty:
        return {
            "tipo": "informe_simple",
            "total": 0,
            "por_estado": {},
            "por_triage": {},
            "en_atencion_o_espera": 0,
            "atendidas": 0,
            "cola": [],
        }
    est = df["estado"].fillna("—").astype(str).str.lower() if "estado" in df.columns else None
    por_estado = {str(k): int(v) for k, v in est.value_counts().items()} if est is not None else {}
    por_triage = {}
    if "triage" in df.columns:
        por_triage = {
            str(k).upper(): int(v)
            for k, v in df["triage"].fillna("—").astype(str).str.upper().value_counts().items()
        }
    en_triage = por_estado.get("triage", 0) + por_estado.get("en_espera", 0)
    activos = {"triage", "en_espera", "registrado"}
    cola_df = df
    if est is not None:
        cola_df = df[est.isin(activos)]
    if not cola_df.empty and "triage" in cola_df.columns:
        orden_t = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4}
        cola_df = cola_df.assign(
            _t=cola_df["triage"].astype(str).str.upper().map(lambda x: orden_t.get(x, 9))
        )
        sort_cols = ["_t"]
        if "hora_llegada" in cola_df.columns:
            sort_cols.append("hora_llegada")
        cola_df = cola_df.sort_values(sort_cols).drop(columns=["_t"], errors="ignore")
    cola_rows = cola_df.head(8).fillna("").to_dict(orient="records")
    return {
        "tipo": "informe_simple",
        "total": int(len(df)),
        "por_estado": por_estado,
        "por_triage": por_triage,
        "en_atencion_o_espera": en_triage + por_estado.get("registrado", 0),
        "atendidas": por_estado.get("atendida", 0),
        "cola": enriquecer(cola_rows),
    }

