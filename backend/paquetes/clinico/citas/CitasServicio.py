import io
import uuid
import pandas as pd
from datetime import date, datetime
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/citas.parquet"
COLUMNAS = [
    "id_cita", "id_paciente", "paciente_nombre", "medico", "fecha", "hora",
    "estado", "motivo", "sede", "notas", "proximo_control", "creado_en", "actualizado_en",
]
ESTADOS = {"programada", "confirmada", "atendida", "cancelada", "no_asistio"}


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
    except Exception:
        pass
    return datos


def hoy() -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "citas": []}
    h = date.today().isoformat()
    sub = df[df["fecha"].astype(str).str.startswith(h)]
    sub = sub.sort_values("hora")
    return {"total": len(sub), "citas": sub.fillna("").to_dict(orient="records")}


def listar(offset: int = 0, limit: int = 50, fecha: str = "", estado: str = "", q: str = "") -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "citas": []}
    if fecha:
        df = df[df["fecha"].astype(str).str.startswith(fecha)]
    if estado:
        df = df[df["estado"] == estado]
    if q:
        ql = q.lower()
        df = df[df["paciente_nombre"].astype(str).str.lower().str.contains(ql, na=False)]
    total = len(df)
    chunk = df.sort_values(["fecha", "hora"], ascending=[False, True]).iloc[offset:offset + limit]
    return {"total": total, "citas": chunk.fillna("").to_dict(orient="records")}


def _nombre_medico(id_usuario: str) -> str:
    try:
        from paquetes.usuarios.UsuariosServicio import obtener_usuario
        u = obtener_usuario(str(id_usuario))
        if "error" not in u:
            return str(u.get("nombre") or "").strip()
    except Exception:
        pass
    return ""


def listar_por_medico(
    id_usuario: str,
    offset: int = 0,
    limit: int = 50,
    fecha: str = "",
    estado: str = "",
    nombre_jwt: str = "",
) -> dict:
    nombre = _nombre_medico(id_usuario) or str(nombre_jwt or "").strip()
    if not nombre:
        return {"total": 0, "medico": "", "citas": []}
    df = _extraer()
    if df.empty:
        return {"total": 0, "medico": nombre, "citas": []}
    nl = nombre.lower()
    df = df[df["medico"].astype(str).str.strip().str.lower() == nl]
    if fecha:
        df = df[df["fecha"].astype(str).str.startswith(fecha)]
    if estado:
        df = df[df["estado"] == estado]
    total = len(df)
    chunk = df.sort_values(["fecha", "hora"], ascending=[False, True]).iloc[offset:offset + limit]
    return {"total": total, "medico": nombre, "citas": chunk.fillna("").to_dict(orient="records")}


def actualizar_estado_medico(
    id_cita: str, id_usuario: str, estado: str, nombre_jwt: str = "",
) -> dict:
    nombre = _nombre_medico(id_usuario) or str(nombre_jwt or "").strip()
    if not nombre:
        return {"error": "Médico no encontrado"}
    permitidos = {"confirmada", "atendida", "no_asistio"}
    estado = str(estado or "").strip()
    if estado not in permitidos:
        return {"error": f"Estado no permitido. Use: {', '.join(sorted(permitidos))}"}
    df = _extraer()
    idx = df.index[df["id_cita"].astype(str) == str(id_cita)].tolist()
    if not idx:
        return {"error": "Cita no encontrada"}
    asignado = str(df.at[idx[0], "medico"]).strip().lower()
    if asignado != nombre.lower():
        return {"error": "La cita no está asignada a este médico"}
    if df.at[idx[0], "estado"] == "cancelada":
        return {"error": "La cita está cancelada"}
    return actualizar(id_cita, {"estado": estado})


def obtener(id_cita: str) -> dict:
    df = _extraer()
    fila = df[df["id_cita"].astype(str) == str(id_cita)]
    if fila.empty:
        return {"error": "Cita no encontrada"}
    return fila.fillna("").iloc[0].to_dict()


def crear(datos: dict) -> dict:
    datos = _enriquecer_paciente(dict(datos))
    if not datos.get("id_paciente"):
        return {"error": "id_paciente es obligatorio"}
    estado = str(datos.get("estado") or "programada")
    if estado not in ESTADOS:
        return {"error": f"estado inválido. Use: {', '.join(sorted(ESTADOS))}"}
    now = datetime.utcnow().isoformat()
    nuevo = {
        "id_cita": str(uuid.uuid4()),
        "id_paciente": str(datos["id_paciente"]),
        "paciente_nombre": str(datos.get("paciente_nombre") or ""),
        "medico": str(datos.get("medico") or ""),
        "fecha": str(datos.get("fecha") or date.today().isoformat()),
        "hora": str(datos.get("hora") or "09:00"),
        "estado": estado,
        "motivo": str(datos.get("motivo") or "Control clínico"),
        "sede": str(datos.get("sede") or "Sede principal"),
        "notas": str(datos.get("notas") or ""),
        "proximo_control": str(datos.get("proximo_control") or ""),
        "creado_en": now,
        "actualizado_en": now,
    }
    df = _extraer()
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return {"mensaje": "Cita agendada", "id_cita": nuevo["id_cita"]}


def actualizar(id_cita: str, cambios: dict) -> dict:
    df = _extraer()
    idx = df.index[df["id_cita"].astype(str) == str(id_cita)].tolist()
    if not idx:
        return {"error": "Cita no encontrada"}
    cambios = _enriquecer_paciente(cambios) if cambios.get("id_paciente") else cambios
    for k, v in cambios.items():
        if k in COLUMNAS and k not in ("id_cita", "creado_en"):
            df.at[idx[0], k] = v
    df.at[idx[0], "actualizado_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    return {"mensaje": "Cita actualizada", "id_cita": id_cita}


def cancelar(id_cita: str) -> dict:
    return actualizar(id_cita, {"estado": "cancelada"})
