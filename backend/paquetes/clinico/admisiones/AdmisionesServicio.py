import uuid
import pandas as pd
from datetime import datetime
from nucleo.utilidades.ParquetCache import leer, escribir
from nucleo.utilidades.Validaciones import rango_fechas_ok

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/admisiones.parquet"
COLUMNAS = [
    "id_admision", "id_paciente", "paciente_nombre", "documento", "tipo", "via_llegada",
    "servicio",
    "medico_id", "medico_nombre", "sede", "habitacion", "estado", "motivo",
    "fecha_ingreso", "fecha_egreso", "notas", "creado_en", "actualizado_en",
]
ESTADOS = {"programada", "activa", "alta", "cancelada"}
TIPOS = {"ambulatoria", "urgencia", "hospitalizacion"}
VIAS = {"propia", "ambulancia", "referido"}


def _extraer(copiar: bool = True) -> pd.DataFrame:
    df = leer(BUCKET_APP, ARCHIVO, COLUMNAS, copiar=copiar)
    return df if not df.empty else pd.DataFrame(columns=COLUMNAS)


def _cargar(df: pd.DataFrame):
    cols = [c for c in COLUMNAS if c in df.columns]
    escribir(BUCKET_APP, ARCHIVO, df[cols] if cols else df)


def _enriquecer_paciente(datos: dict) -> dict:
    pid = datos.get("id_paciente")
    if not pid:
        return datos
    try:
        from paquetes.clinico.pacientes.PacientesServicio import obtener
        p = obtener(str(pid))
        if "error" not in p:
            datos.setdefault("paciente_nombre", p.get("nombre_completo", ""))
            datos.setdefault("documento", p.get("documento", ""))
    except Exception:
        pass
    return datos


def resumen() -> dict:
    df = _extraer(copiar=False)
    if df.empty:
        return {"total": 0, "activas": 0, "altas": 0}
    activas = int((df["estado"] == "activa").sum()) if "estado" in df.columns else 0
    altas = int((df["estado"] == "alta").sum()) if "estado" in df.columns else 0
    return {"total": len(df), "activas": activas, "altas": altas}


def listar(offset: int = 0, limit: int = 50, estado: str = "", q: str = "") -> dict:
    from nucleo.utilidades.Busqueda import rankear_dataframe

    df = _extraer(copiar=False)
    if df.empty:
        return {"total": 0, "admisiones": []}
    if estado:
        df = df[df["estado"] == estado]
    if q:
        df = rankear_dataframe(
            df, q,
            ["paciente_nombre", "documento", "medico_nombre", "servicio", "tipo", "estado", "motivo", "sede"],
        )
    elif "fecha_ingreso" in df.columns:
        df = df.sort_values("fecha_ingreso", ascending=False)
    total = len(df)
    chunk = df.iloc[offset:offset + limit]
    rows = chunk.fillna("").to_dict(orient="records")
    ids = {str(r.get("id_paciente") or "") for r in rows if r.get("id_paciente")}
    mapa = {}
    if ids:
        try:
            from nucleo.utilidades.PacientesLookup import mapa_pacientes
            mapa = mapa_pacientes(ids)
        except Exception:
            mapa = {}
    out = []
    for r in rows:
        x = dict(r)
        x["id_admision"] = str(x.get("id_admision") or "")
        x["id_paciente"] = str(x.get("id_paciente") or "")
        pid = str(x.get("id_paciente") or "")
        p = mapa.get(pid) or {}
        if p.get("nombre_completo") and not str(x.get("paciente_nombre") or "").strip():
            x["paciente_nombre"] = p["nombre_completo"]
        if p.get("documento") and not str(x.get("documento") or "").strip():
            x["documento"] = p["documento"]
        x["tiene_foto"] = bool(p.get("tiene_foto"))
        out.append(x)
    return {"total": total, "admisiones": out}


def obtener(id_admision: str) -> dict:
    df = _extraer()
    fila = df[df["id_admision"].astype(str) == str(id_admision)]
    if fila.empty:
        return {"error": "Admisión no encontrada"}
    return fila.fillna("").iloc[0].to_dict()


def crear(datos: dict) -> dict:
    datos = _enriquecer_paciente(dict(datos))
    if not datos.get("id_paciente"):
        return {"error": "id_paciente es obligatorio"}
    tipo = str(datos.get("tipo") or "ambulatoria")
    if tipo not in TIPOS:
        return {"error": f"tipo inválido. Use: {', '.join(sorted(TIPOS))}"}
    via = str(datos.get("via_llegada") or "propia").lower()
    if via not in VIAS:
        return {"error": "Vía de llegada inválida. Use: propia, ambulancia o referido."}
    if via == "ambulancia" and tipo == "ambulatoria":
        tipo = "urgencia"
    estado = str(datos.get("estado") or "activa")
    if estado not in ESTADOS:
        return {"error": f"estado inválido. Use: {', '.join(sorted(ESTADOS))}"}
    now = datetime.utcnow().isoformat()
    ingreso = str(datos.get("fecha_ingreso") or now[:10])
    egreso = str(datos.get("fecha_egreso") or "")
    err_f = rango_fechas_ok(ingreso, egreso)
    if err_f:
        return {"error": err_f}
    nuevo = {
        "id_admision": str(uuid.uuid4()),
        "id_paciente": str(datos["id_paciente"]),
        "paciente_nombre": str(datos.get("paciente_nombre") or ""),
        "documento": str(datos.get("documento") or ""),
        "tipo": tipo,
        "via_llegada": via,
        "servicio": str(datos.get("servicio") or "Medicina interna"),
        "medico_id": str(datos.get("medico_id") or ""),
        "medico_nombre": str(datos.get("medico_nombre") or ""),
        "sede": str(datos.get("sede") or "Sede principal"),
        "habitacion": str(datos.get("habitacion") or ""),
        "estado": estado,
        "motivo": str(datos.get("motivo") or ""),
        "fecha_ingreso": ingreso,
        "fecha_egreso": egreso,
        "notas": str(datos.get("notas") or ""),
        "creado_en": now,
        "actualizado_en": now,
    }
    df = _extraer()
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    try:
        from paquetes.notificaciones.NotificacionesServicio import emitir_a_roles
        pac = nuevo.get("paciente_nombre") or nuevo.get("id_paciente") or "Paciente"
        emitir_a_roles(
            "Nueva admisión hospitalaria",
            f"{pac}: ingreso {nuevo.get('tipo')} · {nuevo.get('servicio')} · "
            f"médico {nuevo.get('medico_nombre') or 'por asignar'}.",
            "info",
            roles=["medico", "enfermero"],
            referencia_tipo="admision",
            referencia_id=nuevo["id_admision"],
        )
    except Exception:
        pass
    return {"mensaje": "Admisión registrada", "id_admision": nuevo["id_admision"]}


def actualizar(id_admision: str, cambios: dict) -> dict:
    df = _extraer()
    idx = df.index[df["id_admision"].astype(str) == str(id_admision)].tolist()
    if not idx:
        return {"error": "Admisión no encontrada"}
    cambios = _enriquecer_paciente(cambios) if cambios.get("id_paciente") else cambios
    if cambios.get("tipo") and str(cambios["tipo"]) not in TIPOS:
        return {"error": f"tipo inválido. Use: {', '.join(sorted(TIPOS))}"}
    if cambios.get("via_llegada") and str(cambios["via_llegada"]).lower() not in VIAS:
        return {"error": "Vía de llegada inválida. Use: propia, ambulancia o referido."}
    via_prev = ""
    if "via_llegada" in df.columns:
        via_prev = df.at[idx[0], "via_llegada"]
    via = str(cambios.get("via_llegada") or via_prev or "propia").lower()
    tipo = str(cambios.get("tipo") or df.at[idx[0], "tipo"] or "ambulatoria")
    if via == "ambulancia" and tipo == "ambulatoria":
        cambios["tipo"] = "urgencia"
    ingreso = str(cambios.get("fecha_ingreso") or df.at[idx[0], "fecha_ingreso"] or "")
    egreso = str(cambios.get("fecha_egreso") if "fecha_egreso" in cambios else df.at[idx[0], "fecha_egreso"] or "")
    err_f = rango_fechas_ok(ingreso, egreso)
    if err_f:
        return {"error": err_f}
    for k, v in cambios.items():
        if k in COLUMNAS and k not in ("id_admision", "creado_en"):
            df.at[idx[0], k] = v
    df.at[idx[0], "actualizado_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    return {"mensaje": "Admisión actualizada", "id_admision": id_admision}
