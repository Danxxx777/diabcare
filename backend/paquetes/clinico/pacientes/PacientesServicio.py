import uuid
import pandas as pd
from datetime import datetime
from nucleo.utilidades.ParquetCache import leer, escribir

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/pacientes.parquet"
COLUMNAS = [
    "id_paciente", "codigo", "nombre", "apellido", "documento", "edad", "genero",
    "telefono", "email", "sede", "estado", "notas", "creado_en", "actualizado_en",
]


def _extraer() -> pd.DataFrame:
    return leer(BUCKET_APP, ARCHIVO, COLUMNAS)


def _cargar(df: pd.DataFrame):
    escribir(BUCKET_APP, ARCHIVO, df)


def _ids_con_foto_paciente() -> set[str]:
    try:
        from paquetes.clinico.pacientes.FotosEntidadServicio import _extraer as fotos_df, _es_true
        fdf = fotos_df()
        if fdf.empty:
            return set()
        sub = fdf[
            (fdf["tipo_entidad"].astype(str) == "paciente")
            & fdf["es_principal"].map(_es_true)
        ]
        return set(sub["id_entidad"].astype(str).tolist())
    except Exception:
        return set()


def _fila_a_dict(row, fotos: set[str] | None = None) -> dict:
    d = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    out = {k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in d.items()}
    out["nombre_completo"] = f"{out.get('nombre') or ''} {out.get('apellido') or ''}".strip()
    pid = str(out.get("id_paciente", ""))
    if fotos is not None:
        out["tiene_foto"] = pid in fotos
    else:
        try:
            from paquetes.clinico.pacientes.FotosEntidadServicio import obtener_principal
            out["tiene_foto"] = bool(obtener_principal("paciente", pid))
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
    from nucleo.utilidades.Busqueda import rankear_dataframe

    df = _extraer()
    if df.empty:
        return {"total": 0, "pacientes": []}
    if estado:
        df = df[df["estado"] == estado]
    if q:
        if "nombre" in df.columns and "apellido" in df.columns:
            df = df.assign(_nombre_completo=(df["nombre"].astype(str) + " " + df["apellido"].astype(str)))
        df = rankear_dataframe(
            df, q,
            ["documento", "codigo", "nombre", "apellido", "_nombre_completo", "sede", "email", "telefono"],
        )
        if "_nombre_completo" in df.columns:
            df = df.drop(columns=["_nombre_completo"])
    total = len(df)
    chunk = df.iloc[offset:offset + limit]
    fotos = _ids_con_foto_paciente()
    kp = resumen()
    return {
        "total": total,
        "pacientes": [_fila_a_dict(r, fotos) for _, r in chunk.iterrows()],
        "resumen": kp,
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
        return {"error": "Ya existe un paciente con esa cédula"}
    now = datetime.utcnow().isoformat()
    year = datetime.utcnow().year
    nuevo = {
        "id_paciente": str(uuid.uuid4()),
        "codigo": str(datos.get("codigo") or f"HC-{year}-{len(df)+1:05d}"),
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
