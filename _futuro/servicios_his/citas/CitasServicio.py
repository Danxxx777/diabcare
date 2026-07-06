"""Agenda clínica — citas y estados de seguimiento."""

from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from servicios.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/citas.parquet"
ESTADOS = frozenset({
    "programada", "en_consulta", "completada", "no_asistio", "cancelada",
})
COLUMNAS = [
    "id_cita", "id_paciente", "paciente_nombre", "medico", "fecha", "hora",
    "estado", "motivo", "sede", "notas", "proximo_control", "creado_en", "actualizado_en",
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


def _cargar(df: pd.DataFrame) -> None:
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, ARCHIVO, buf, buf.getbuffer().nbytes)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def listar(
    fecha: str = "",
    estado: str = "",
    id_paciente: str = "",
    limit: int = 100,
) -> dict:
    df = _extraer()
    if df.empty:
        return {"citas": [], "total": 0}
    if fecha:
        df = df[df["fecha"].astype(str) == str(fecha)[:10]]
    if estado:
        df = df[df["estado"] == estado]
    if id_paciente:
        df = df[df["id_paciente"].astype(str) == str(id_paciente)]
    df = df.sort_values(["fecha", "hora"], ascending=[True, True])
    total = len(df)
    rows = df.head(limit).fillna("").to_dict(orient="records")
    return {"citas": rows, "total": total}


def listar_hoy(fecha: str | None = None) -> dict:
    f = (fecha or date.today().isoformat())[:10]
    return listar(fecha=f, limit=200)


def crear(datos: dict, medico: str = "sistema") -> dict:
    id_paciente = str(datos.get("id_paciente", "")).strip()
    if not id_paciente:
        return {"error": "id_paciente requerido"}

    from servicios.pacientes.PacientesServicio import obtener
    pac = obtener(id_paciente)
    if pac.get("error"):
        return pac

    estado = str(datos.get("estado", "programada"))
    if estado not in ESTADOS:
        estado = "programada"

    ahora = _ahora()
    fila = {
        "id_cita": str(uuid.uuid4()),
        "id_paciente": id_paciente,
        "paciente_nombre": pac.get("nombre_completo", ""),
        "medico": str(datos.get("medico") or medico),
        "fecha": str(datos.get("fecha", date.today().isoformat()))[:10],
        "hora": str(datos.get("hora", "09:00"))[:5],
        "estado": estado,
        "motivo": str(datos.get("motivo", "Consulta de control")),
        "sede": str(datos.get("sede") or pac.get("sede", "California")),
        "notas": str(datos.get("notas", "")),
        "proximo_control": str(datos.get("proximo_control", ""))[:10],
        "creado_en": ahora,
        "actualizado_en": ahora,
    }
    df = _extraer()
    _cargar(pd.concat([df, pd.DataFrame([fila])], ignore_index=True))
    return {"mensaje": "Cita programada", "cita": fila}


def actualizar_estado(id_cita: str, estado: str, notas: str = "") -> dict:
    if estado not in ESTADOS:
        return {"error": f"Estado inválido. Use: {', '.join(sorted(ESTADOS))}"}
    df = _extraer()
    idx = df.index[df["id_cita"] == id_cita].tolist()
    if not idx:
        return {"error": "Cita no encontrada"}
    df.at[idx[0], "estado"] = estado
    if notas:
        df.at[idx[0], "notas"] = notas
    df.at[idx[0], "actualizado_en"] = _ahora()
    _cargar(df)
    cita = df.iloc[idx[0]].fillna("").to_dict()
    return {"mensaje": "Estado actualizado", "cita": cita}


def completar(id_cita: str, notas: str = "", programar_seguimiento: bool = True) -> dict:
    res = actualizar_estado(id_cita, "completada", notas)
    if res.get("error"):
        return res
    cita = res["cita"]
    if not programar_seguimiento:
        return res
    try:
        f = datetime.strptime(str(cita["fecha"])[:10], "%Y-%m-%d").date()
        seg = (f + timedelta(days=90)).isoformat()
        df = _extraer()
        idx = df.index[df["id_cita"] == id_cita].tolist()
        if idx:
            df.at[idx[0], "proximo_control"] = seg
            _cargar(df)
        seg_res = crear({
            "id_paciente": cita["id_paciente"],
            "fecha": seg,
            "hora": cita.get("hora", "09:00"),
            "motivo": "Control de seguimiento (3 meses)",
            "sede": cita.get("sede", ""),
            "medico": cita.get("medico", ""),
        }, medico=str(cita.get("medico", "sistema")))
        res["seguimiento"] = seg_res.get("cita")
    except Exception:
        pass
    return res
