"""Admisiones hospitalarias — ingreso, tipo de atención y egreso."""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

import pandas as pd

from servicios.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/admisiones.parquet"
TIPOS = ("ambulatoria", "urgencia", "hospitalizacion")
ESTADOS = ("activa", "alta", "cancelada")
COLUMNAS = [
    "id_admision", "id_paciente", "paciente_nombre", "documento", "tipo", "servicio",
    "medico_id", "medico_nombre", "sede", "habitacion", "estado", "motivo",
    "fecha_ingreso", "fecha_egreso", "notas", "creado_en", "actualizado_en",
]


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extraer() -> pd.DataFrame:
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)


def _cargar(df: pd.DataFrame) -> None:
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, ARCHIVO, buf, buf.getbuffer().nbytes)


def listar(q: str = "", tipo: str = "", estado: str = "", limit: int = 80) -> dict:
    df = _extraer()
    if df.empty:
        return {"admisiones": [], "total": 0}
    if tipo:
        df = df[df["tipo"] == tipo]
    if estado:
        df = df[df["estado"] == estado]
    if q:
        ql = q.lower()
        mask = (
            df["paciente_nombre"].astype(str).str.lower().str.contains(ql, na=False)
            | df["documento"].astype(str).str.lower().str.contains(ql, na=False)
            | df["id_admision"].astype(str).str.lower().str.contains(ql, na=False)
        )
        df = df[mask]
    df = df.sort_values("fecha_ingreso", ascending=False)
    total = len(df)
    rows = df.head(limit).fillna("").to_dict(orient="records")
    return {"admisiones": rows, "total": int(total)}


def crear(datos: dict, usuario: str = "sistema") -> dict:
    id_paciente = str(datos.get("id_paciente", "")).strip()
    if not id_paciente:
        return {"error": "id_paciente requerido"}

    from servicios.pacientes.PacientesServicio import obtener
    pac = obtener(id_paciente)
    if pac.get("error"):
        return pac

    tipo = str(datos.get("tipo", "ambulatoria"))
    if tipo not in TIPOS:
        tipo = "ambulatoria"

    ahora = _ahora()
    fila = {
        "id_admision": f"ADM-{uuid.uuid4().hex[:8].upper()}",
        "id_paciente": id_paciente,
        "paciente_nombre": pac.get("nombre_completo") or f"{pac.get('nombre', '')} {pac.get('apellido', '')}".strip(),
        "documento": str(pac.get("documento", "")),
        "tipo": tipo,
        "servicio": str(datos.get("servicio", "Medicina interna")),
        "medico_id": str(datos.get("medico_id", "")),
        "medico_nombre": str(datos.get("medico_nombre", usuario)),
        "sede": str(datos.get("sede") or pac.get("sede", "California")),
        "habitacion": str(datos.get("habitacion", "")),
        "estado": "activa",
        "motivo": str(datos.get("motivo", "Ingreso hospitalario")),
        "fecha_ingreso": str(datos.get("fecha_ingreso", ahora))[:19],
        "fecha_egreso": "",
        "notas": str(datos.get("notas", "")),
        "creado_en": ahora,
        "actualizado_en": ahora,
    }
    df = _extraer()
    df = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
    _cargar(df)
    return fila


def registrar_egreso(id_admision: str, notas: str = "") -> dict:
    df = _extraer()
    idx = df.index[df["id_admision"].astype(str) == str(id_admision)]
    if len(idx) == 0:
        return {"error": "Admisión no encontrada"}
    i = idx[0]
    if df.at[i, "estado"] != "activa":
        return {"error": "La admisión ya fue cerrada"}
    df.at[i, "estado"] = "alta"
    df.at[i, "fecha_egreso"] = _ahora()[:19]
    if notas:
        df.at[i, "notas"] = str(df.at[i, "notas"] or "") + (" | Egreso: " + notas)
    df.at[i, "actualizado_en"] = _ahora()
    _cargar(df)
    return df.loc[i].fillna("").to_dict()


def resumen() -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "activas": 0, "altas_hoy": 0, "por_tipo": {}}
    activas = df[df["estado"] == "activa"]
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    altas_hoy = df[(df["estado"] == "alta") & df["fecha_egreso"].astype(str).str.startswith(hoy)]
    por_tipo = activas.groupby("tipo").size().to_dict() if not activas.empty else {}
    return {
        "total": len(df),
        "activas": len(activas),
        "altas_hoy": len(altas_hoy),
        "por_tipo": {str(k): int(v) for k, v in por_tipo.items()},
    }
