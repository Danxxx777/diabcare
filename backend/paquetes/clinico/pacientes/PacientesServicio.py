import io
import uuid
import pandas as pd
from datetime import datetime
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/pacientes.parquet"
COLUMNAS = [
    "id_paciente", "codigo", "nombre", "apellido", "documento", "edad", "genero",
    "telefono", "email", "sede", "estado", "notas", "creado_en", "actualizado_en",
]


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


def _fila_a_dict(row) -> dict:
    d = row.to_dict()
    out = {k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in d.items()}
    out["nombre_completo"] = f"{out.get('nombre') or ''} {out.get('apellido') or ''}".strip()
    try:
        from paquetes.clinico.pacientes.FotosEntidadServicio import obtener_principal
        if obtener_principal("paciente", str(out.get("id_paciente", ""))):
            out["tiene_foto"] = True
        else:
            out["tiene_foto"] = False
    except Exception:
        out["tiene_foto"] = False
    return out


def resumen() -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "activos": 0, "inactivos": 0}
    if "estado" not in df.columns:
        return {"total": len(df), "activos": len(df), "inactivos": 0}
    activos = int((df["estado"] == "activo").sum())
    return {"total": len(df), "activos": activos, "inactivos": len(df) - activos}


def listar(offset: int = 0, limit: int = 50, q: str = "", estado: str = "") -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "pacientes": []}
    if estado:
        df = df[df["estado"] == estado]
    if q:
        ql = q.lower()
        mask = (
            df["nombre"].astype(str).str.lower().str.contains(ql, na=False)
            | df["apellido"].astype(str).str.lower().str.contains(ql, na=False)
            | df["documento"].astype(str).str.lower().str.contains(ql, na=False)
            | df["codigo"].astype(str).str.lower().str.contains(ql, na=False)
        )
        df = df[mask]
    total = len(df)
    chunk = df.iloc[offset:offset + limit]
    return {
        "total": total,
        "pacientes": [_fila_a_dict(r) for _, r in chunk.iterrows()],
    }


def obtener(id_paciente: str) -> dict:
    df = _extraer()
    fila = df[df["id_paciente"].astype(str) == str(id_paciente)]
    if fila.empty:
        return {"error": "Paciente no encontrado"}
    return _fila_a_dict(fila.iloc[0])


def crear(datos: dict) -> dict:
    df = _extraer()
    doc = str(datos.get("documento") or "").strip()
    if doc and not df.empty and doc in df["documento"].astype(str).values:
        return {"error": "Ya existe un paciente con ese documento"}
    now = datetime.utcnow().isoformat()
    nuevo = {
        "id_paciente": str(uuid.uuid4()),
        "codigo": str(datos.get("codigo") or f"P{len(df)+1:05d}"),
        "nombre": str(datos.get("nombre") or "").strip(),
        "apellido": str(datos.get("apellido") or "").strip(),
        "documento": doc,
        "edad": float(datos.get("edad") or 0),
        "genero": str(datos.get("genero") or "Femenino"),
        "telefono": str(datos.get("telefono") or ""),
        "email": str(datos.get("email") or ""),
        "sede": str(datos.get("sede") or "Sede principal"),
        "estado": "activo",
        "notas": str(datos.get("notas") or ""),
        "creado_en": now,
        "actualizado_en": now,
    }
    if not nuevo["nombre"]:
        return {"error": "El nombre es obligatorio"}
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return {"mensaje": "Paciente creado", "id_paciente": nuevo["id_paciente"]}


def actualizar(id_paciente: str, cambios: dict) -> dict:
    df = _extraer()
    idx = df.index[df["id_paciente"].astype(str) == str(id_paciente)].tolist()
    if not idx:
        return {"error": "Paciente no encontrado"}
    for k, v in cambios.items():
        if k in COLUMNAS and k not in ("id_paciente", "creado_en"):
            df.at[idx[0], k] = v
    df.at[idx[0], "actualizado_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    return {"mensaje": "Paciente actualizado", "id_paciente": id_paciente}


def desactivar(id_paciente: str) -> dict:
    return actualizar(id_paciente, {"estado": "inactivo"})
