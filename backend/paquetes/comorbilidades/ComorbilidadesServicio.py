"""Extensión P3 — comorbilidades / complicaciones del paciente diabético."""
from nucleo.utilidades.ParquetStore import ParquetStore
from nucleo.utilidades.PacientesLookup import mapa_pacientes

TIPOS = {"retinopatia", "nefropatia", "neuropatia", "cardiovascular", "pie_diabetico"}

TIPOS_LABEL = {
    "retinopatia": "Retinopatía",
    "nefropatia": "Nefropatía",
    "neuropatia": "Neuropatía",
    "cardiovascular": "Cardiovascular",
    "pie_diabetico": "Pie diabético",
}

ESTADOS_LABEL = {
    "activa": "Activa",
    "activo": "Activa",
    "anulado": "Anulada",
    "anulada": "Anulada",
    "inactiva": "Inactiva",
}

comorbilidades = ParquetStore(
    "negocio/oper_comorbilidades_paciente.parquet",
    ["id_comorbilidad", "id_paciente", "tipo", "fecha_deteccion", "id_medico",
     "notas", "estado", "creado_en", "actualizado_en"],
    "id_comorbilidad", "comorbilidades", modo_borrado="estado",
)


def enriquecer(filas: list) -> list:
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
        x["paciente_label"] = x["paciente_nombre"]  # solo nombre; cédula va en su columna
        x["tiene_foto"] = bool(p.get("tiene_foto"))

        tipo = str(x.get("tipo") or "").lower()
        x["tipo_label"] = TIPOS_LABEL.get(tipo, tipo.replace("_", " ").title() or "—")
        est = str(x.get("estado") or "").lower()
        x["estado_label"] = ESTADOS_LABEL.get(est, (est[:1].upper() + est[1:]) if est else "—")
        out.append(x)
    return out


def listar_enriquecido(**kwargs) -> dict:
    q = str(kwargs.pop("q", "") or "").strip()
    offset = int(kwargs.get("offset") or 0)
    limit = int(kwargs.get("limit") or 50)
    q_campos = kwargs.pop("q_campos", None)  # no aplica sobre columnas crudas
    if q:
        kwargs = {**kwargs, "offset": 0, "limit": 10**9, "q": ""}
        res = comorbilidades.listar(**kwargs)
        rows = enriquecer(res.get("comorbilidades") or [])
        ql = q.lower()
        tokens = [t for t in ql.replace(",", " ").split() if t]
        campos = ("paciente_nombre", "documento", "tipo", "tipo_label", "estado", "estado_label", "notas", "fecha_deteccion")
        filtradas = []
        for r in rows:
            blob = " ".join(str(r.get(k) or "") for k in campos).lower()
            if ql in blob or (tokens and all(t in blob for t in tokens)):
                filtradas.append(r)
        return {"total": len(filtradas), "comorbilidades": filtradas[offset: offset + limit]}
    res = comorbilidades.listar(**kwargs)
    res["comorbilidades"] = enriquecer(res.get("comorbilidades") or [])
    return res


def resumen_operativo() -> dict:
    """Informe simple: complicaciones registradas por tipo y pacientes afectados."""
    df = comorbilidades.extraer(copiar=False)
    if df.empty:
        return {
            "tipo": "informe_simple",
            "total": 0,
            "pacientes_afectados": 0,
            "por_tipo": {},
            "tipo_mas_frecuente": "",
        }
    work = df
    if "estado" in df.columns:
        est = df["estado"].astype(str).str.lower()
        work = df[~est.isin(["anulada", "anulado"])]
    por_tipo: dict[str, int] = {}
    if not work.empty and "tipo" in work.columns:
        por_tipo = {
            str(k).lower(): int(v)
            for k, v in work["tipo"].fillna("otro").astype(str).str.lower().value_counts().items()
        }
    n_pac = 0
    if not work.empty and "id_paciente" in work.columns:
        ids = work["id_paciente"].astype(str).str.strip()
        n_pac = int(ids[~ids.isin(["", "nan", "None"])].nunique())
    mas_frecuente = max(por_tipo, key=por_tipo.get) if por_tipo else ""
    return {
        "tipo": "informe_simple",
        "total": int(len(work)),
        "pacientes_afectados": n_pac,
        "por_tipo": por_tipo,
        "tipo_mas_frecuente": TIPOS_LABEL.get(mas_frecuente, mas_frecuente),
    }


def crear(datos: dict) -> dict:
    tipo = str(datos.get("tipo") or "").lower().replace("í", "i").replace("á", "a")
    mapa = {
        "retinopatía": "retinopatia", "retinopatia": "retinopatia",
        "nefropatía": "nefropatia", "nefropatia": "nefropatia",
        "neuropatía": "neuropatia", "neuropatia": "neuropatia",
        "cardiovascular": "cardiovascular",
        "pie_diabetico": "pie_diabetico", "pie diabético": "pie_diabetico", "pie_diabético": "pie_diabetico",
    }
    tipo_n = mapa.get(str(datos.get("tipo") or "").lower(), tipo)
    if tipo_n not in TIPOS:
        return {"error": f"tipo inválido. Use: {', '.join(sorted(TIPOS))}"}
    if not datos.get("id_paciente") or not datos.get("id_medico") or not datos.get("fecha_deteccion"):
        return {"error": "RN-COM-001: requiere id_paciente, id_medico y fecha_deteccion"}
    return comorbilidades.crear({
        "id_paciente": str(datos["id_paciente"]),
        "tipo": tipo_n,
        "fecha_deteccion": str(datos["fecha_deteccion"]),
        "id_medico": str(datos["id_medico"]),
        "notas": str(datos.get("notas") or ""),
        "estado": "activa",
    })
