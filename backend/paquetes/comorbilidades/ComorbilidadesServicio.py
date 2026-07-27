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
    res = comorbilidades.listar(**kwargs)
    res["comorbilidades"] = enriquecer(res.get("comorbilidades") or [])
    return res


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
