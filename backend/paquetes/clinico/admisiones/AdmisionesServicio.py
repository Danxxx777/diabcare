import io
import uuid
import pandas as pd
from datetime import datetime
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/admisiones.parquet"
COLUMNAS = [
    "id_admision", "id_paciente", "paciente_nombre", "documento", "tipo", "servicio",
    "medico_id", "medico_nombre", "sede", "habitacion", "estado", "motivo",
    "fecha_ingreso", "fecha_egreso", "notas", "creado_en", "actualizado_en",
]
ESTADOS = {"programada", "activa", "alta", "cancelada"}
TIPOS = {"ambulatoria", "urgencia", "hospitalizacion"}


def _extraer() -> pd.DataFrame:
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)


def _cargar(df: pd.DataFrame):
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, ARCHIVO, buf, buf.getbuffer().nbytes)


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
    df = _extraer()
    if df.empty:
        return {"total": 0, "activas": 0, "altas": 0}
    activas = int((df["estado"] == "activa").sum()) if "estado" in df.columns else 0
    altas = int((df["estado"] == "alta").sum()) if "estado" in df.columns else 0
    return {"total": len(df), "activas": activas, "altas": altas}


def listar(offset: int = 0, limit: int = 50, estado: str = "", q: str = "") -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "admisiones": []}
    if estado:
        df = df[df["estado"] == estado]
    if q:
        ql = q.lower()
        df = df[df["paciente_nombre"].astype(str).str.lower().str.contains(ql, na=False)]
    total = len(df)
    chunk = df.sort_values("fecha_ingreso", ascending=False).iloc[offset:offset + limit]
    return {"total": total, "admisiones": chunk.fillna("").to_dict(orient="records")}


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
    estado = str(datos.get("estado") or "activa")
    if estado not in ESTADOS:
        return {"error": f"estado inválido. Use: {', '.join(sorted(ESTADOS))}"}
    now = datetime.utcnow().isoformat()
    nuevo = {
        "id_admision": str(uuid.uuid4()),
        "id_paciente": str(datos["id_paciente"]),
        "paciente_nombre": str(datos.get("paciente_nombre") or ""),
        "documento": str(datos.get("documento") or ""),
        "tipo": tipo,
        "servicio": str(datos.get("servicio") or "Medicina interna"),
        "medico_id": str(datos.get("medico_id") or ""),
        "medico_nombre": str(datos.get("medico_nombre") or ""),
        "sede": str(datos.get("sede") or "Sede principal"),
        "habitacion": str(datos.get("habitacion") or ""),
        "estado": estado,
        "motivo": str(datos.get("motivo") or ""),
        "fecha_ingreso": str(datos.get("fecha_ingreso") or now[:10]),
        "fecha_egreso": str(datos.get("fecha_egreso") or ""),
        "notas": str(datos.get("notas") or ""),
        "creado_en": now,
        "actualizado_en": now,
    }
    df = _extraer()
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return {"mensaje": "Admisión registrada", "id_admision": nuevo["id_admision"]}


def actualizar(id_admision: str, cambios: dict) -> dict:
    df = _extraer()
    idx = df.index[df["id_admision"].astype(str) == str(id_admision)].tolist()
    if not idx:
        return {"error": "Admisión no encontrada"}
    cambios = _enriquecer_paciente(cambios) if cambios.get("id_paciente") else cambios
    for k, v in cambios.items():
        if k in COLUMNAS and k not in ("id_admision", "creado_en"):
            df.at[idx[0], k] = v
    df.at[idx[0], "actualizado_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    return {"mensaje": "Admisión actualizada", "id_admision": id_admision}
