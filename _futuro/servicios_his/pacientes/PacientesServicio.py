"""
PacientesServicio — gestión de expedientes clínicos hospitalarios.
Persistencia en MinIO diabcare-app/pacientes/.
"""

from __future__ import annotations

import io
import threading
import uuid
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

from servicios.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "pacientes/pacientes.parquet"
COLUMNAS = [
    "id_paciente", "codigo_historia", "nombre", "apellido", "documento",
    "fecha_nacimiento", "genero", "telefono", "email", "sede", "estado",
    "notas", "encounter_origen", "creado_en", "actualizado_en",
]
_cache: dict = {"df": None, "stat": None, "idx": None, "resumen": None}
_hp_cache: dict = {"df": None, "stat": None}
_load_lock = threading.Lock()


def invalidar_cache_pacientes() -> None:
    _cache["df"] = _cache["stat"] = _cache["idx"] = _cache["resumen"] = None


def _stat_archivo() -> tuple | None:
    try:
        st = get_cliente().stat_object(BUCKET_APP, ARCHIVO)
        return (st.etag, st.last_modified, st.size)
    except Exception:
        return None


def _extraer() -> pd.DataFrame:
    st = _stat_archivo()
    if st and _cache["df"] is not None and _cache["stat"] == st:
        return _cache["df"]
    with _load_lock:
        if st and _cache["df"] is not None and _cache["stat"] == st:
            return _cache["df"]
        try:
            c = get_cliente()
            if not c.bucket_exists(BUCKET_APP):
                c.make_bucket(BUCKET_APP)
            obj = c.get_object(BUCKET_APP, ARCHIVO)
            df = pd.read_parquet(io.BytesIO(obj.read()))
            for col in COLUMNAS:
                if col not in df.columns:
                    df[col] = ""
            _cache["df"] = df
            _cache["stat"] = st
            _cache["idx"] = None
            _cache["resumen"] = None
            return df
        except Exception:
            _cache["df"] = pd.DataFrame(columns=COLUMNAS)
            _cache["stat"] = st
            _cache["idx"] = None
            _cache["resumen"] = None
            return _cache["df"]


def _cargar(df: pd.DataFrame) -> None:
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, ARCHIVO, buf, buf.getbuffer().nbytes)
    _cache["df"] = df.copy()
    _cache["stat"] = _stat_archivo()
    _cache["idx"] = None
    _cache["resumen"] = None


def precalentar_cache() -> None:
    """Reservado: el listado ya no precarga 901k filas en memoria."""
    pass


def _abrir_parquet():
    import pyarrow.parquet as pq
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        return None, 0
    obj = c.get_object(BUCKET_APP, ARCHIVO)
    buf = io.BytesIO(obj.read())
    pf = pq.ParquetFile(buf)
    return pf, pf.metadata.num_rows


def _fila_desde_batch(batch, i: int, cols: list[str]) -> dict:
    row = {}
    for col in cols:
        if col not in batch.schema.names:
            row[col] = ""
            continue
        val = batch.column(col)[i].as_py()
        row[col] = "" if val is None else val
    return row


def _ultimas_filas(limit: int, offset: int = 0) -> tuple[list[dict], int]:
    """Lee las últimas filas del parquet sin cargar todo en pandas."""
    pf, total = _abrir_parquet()
    if not pf or total == 0:
        return [], 0
    want_start = max(0, total - offset - limit)
    want_end = max(0, total - offset)
    cols = [c for c in COLUMNAS if c in pf.schema_arrow.names]
    rows: list[dict] = []
    idx = 0
    for batch in pf.iter_batches(batch_size=50000, columns=cols):
        for i in range(batch.num_rows):
            if want_start <= idx < want_end:
                rows.append(_fila_desde_batch(batch, i, cols))
            idx += 1
            if idx >= want_end:
                return rows, total
    return rows, total


def _total_parquet() -> int:
    try:
        _, total = _abrir_parquet()
        return int(total or 0)
    except Exception:
        return 0


def _buscar_paciente(id_paciente: str) -> pd.Series | None:
    df = _extraer()
    if df.empty:
        return None
    if _cache["idx"] is None:
        _cache["idx"] = df.set_index("id_paciente", drop=False)
    if id_paciente not in _cache["idx"].index:
        return None
    row = _cache["idx"].loc[id_paciente]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return row


def _edad_desde_nacimiento(fecha) -> int:
    try:
        if isinstance(fecha, datetime):
            nac = fecha
        elif isinstance(fecha, date):
            nac = datetime(fecha.year, fecha.month, fecha.day)
        else:
            nac = datetime.fromisoformat(str(fecha)[:10])
        hoy = datetime.now()
        return hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    except Exception:
        return 45


def _siguiente_codigo(df: pd.DataFrame) -> str:
    if df.empty or "codigo_historia" not in df.columns:
        return "HC-00001"
    nums = []
    for c in df["codigo_historia"].astype(str):
        if c.startswith("HC-"):
            try:
                nums.append(int(c.split("-")[1]))
            except ValueError:
                pass
    n = max(nums) + 1 if nums else 1
    return f"HC-{n:05d}"


def _a_json(val):
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    if isinstance(val, np.bool_):
        return bool(val)
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    return val


def _filas_json(rows: list[dict]) -> list[dict]:
    return [{k: _a_json(v) for k, v in r.items()} for r in rows]


def _es_documento_legacy(doc: str) -> bool:
    return str(doc or "").strip().startswith("DS-")


def _contar_legacy(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    return int(df["documento"].astype(str).str.startswith("DS-").sum())


def _ordenar_recientes(df: pd.DataFrame) -> pd.DataFrame:
    """Orden descendente por fecha de creación (compatible con strings ISO)."""
    if df.empty:
        return df
    if "creado_en" in df.columns:
        return df.sort_values("creado_en", ascending=False, na_position="last")
    if "encounter_origen" in df.columns:
        return df.sort_values("encounter_origen", ascending=False, na_position="last")
    return df.iloc[::-1]


def _presentar_fila(r: dict) -> dict:
    """Muestra nombres y documento clínico aunque el parquet aún no esté migrado."""
    doc = str(r.get("documento", ""))
    if _es_documento_legacy(doc):
        eid = _encounter_desde_documento(doc)
        if eid is not None:
            fem = "fem" in str(r.get("genero", "")).lower()
            nom, ape = _nombre_apellido(eid, fem)
            r = dict(r)
            r["nombre"] = nom
            r["apellido"] = ape
            r["documento"] = _documento_desde_encounter(eid)
    r["edad"] = _edad_desde_nacimiento(r.get("fecha_nacimiento", ""))
    r["nombre_completo"] = f"{r.get('nombre', '')} {r.get('apellido', '')}".strip()
    return r


def migrar_formato_legacy(actualizar_sedes: bool = True, limite: int = 25000) -> dict:
    """Convierte expedientes DS-000001 → CC X.XXX.XXX con nombres variados (por lotes)."""
    df = _extraer()
    legacy_count = _contar_legacy(df)
    if legacy_count == 0:
        return {"migrados": 0, "formato_legacy": False, "legacy_restantes": 0, "mensaje": "Expedientes ya actualizados"}

    mask = df["documento"].astype(str).str.startswith("DS-")
    idx = df.index[mask][:limite]
    if len(idx) == 0:
        return {"migrados": 0, "formato_legacy": False, "legacy_restantes": 0}

    eids = df.loc[idx, "documento"].astype(str).str.replace("DS-", "", regex=False).astype(int)
    fem = df.loc[idx, "genero"].fillna("Femenino").astype(str).str.lower().str.contains("fem", na=False)

    nombres, apellidos, documentos = [], [], []
    for eid, is_f in zip(eids.to_numpy(), fem.to_numpy()):
        nom, ape = _nombre_apellido(int(eid), bool(is_f))
        nombres.append(nom)
        apellidos.append(ape)
        documentos.append(_documento_desde_encounter(int(eid)))

    ahora = datetime.now(timezone.utc).isoformat()
    df.loc[idx, "nombre"] = nombres
    df.loc[idx, "apellido"] = apellidos
    df.loc[idx, "documento"] = documentos
    df.loc[idx, "encounter_origen"] = eids.astype(int).tolist()
    df.loc[idx, "actualizado_en"] = ahora

    emails = df.loc[idx, "email"].astype(str)
    viejo_email = emails.str.contains(r"paciente\.|@diabcare", regex=True, na=False)
    for row_idx in emails.index[viejo_email]:
        df.at[row_idx, "email"] = f"contacto.{int(eids.loc[row_idx])}@paciente.diabcare.local"

    if actualizar_sedes:
        datos = _obtener_datos_dataset()
        if not datos.empty and "location" in datos.columns:
            sede_map = dict(zip(datos["encounter_id"].astype(int), datos["location"].astype(str)))
            df.loc[idx, "sede"] = [sede_map.get(int(e), df.at[i, "sede"]) for i, e in zip(idx, eids)]

    _cargar(df)
    restantes = _contar_legacy(_extraer())
    vinc = 0
    if restantes == 0:
        datos = _obtener_datos_dataset()
        vinc = _vincular_consultas(datos, _extraer()) if not datos.empty else 0
    return {
        "mensaje": "Expedientes actualizados a formato clínico",
        "migrados": len(idx),
        "legacy_restantes": restantes,
        "formato_legacy": restantes > 0,
        "consultas_vinculadas": vinc,
    }


def listar(q: str = "", estado: str = "", limit: int = 50, offset: int = 0) -> dict:
    try:
        q = (q or "").strip()
        estado = (estado or "").strip()

        # Vista por defecto: sin pandas, sin cargar 901k filas
        if not q and not estado:
            raw, total = _ultimas_filas(limit, offset)
            raw.reverse()
            rows = _filas_json([_presentar_fila(r) for r in raw])
            return {"pacientes": rows, "total": total, "limit": limit, "offset": offset}

        df = _extraer()
        if df.empty:
            return {"pacientes": [], "total": 0, "limit": limit, "offset": offset}
        if estado:
            df = df[df["estado"] == estado]
        ql = q.lower()
        ql_digits = ql.replace(".", "").replace(" ", "")
        docs = df["documento"].astype(str)
        mask = (
            df["nombre"].astype(str).str.lower().str.contains(ql, na=False)
            | df["apellido"].astype(str).str.lower().str.contains(ql, na=False)
            | docs.str.lower().str.replace(".", "", regex=False).str.contains(ql_digits, na=False)
        )
        if ql_digits.isdigit():
            eids = docs.map(_encounter_desde_documento)
            mask = mask | eids.astype(str).str.contains(ql_digits, na=False)
        df = df[mask]
        total = len(df)
        chunk = _ordenar_recientes(df).iloc[offset: offset + limit]
        rows = _filas_json([_presentar_fila(r) for r in chunk.fillna("").to_dict(orient="records")])
        return {"pacientes": rows, "total": int(total), "limit": limit, "offset": offset}
    except Exception as e:
        import logging
        logging.getLogger("diabcare.pacientes").exception("listar: %s", e)
        return {"pacientes": [], "total": 0, "limit": limit, "offset": offset, "error": str(e)}


def obtener(id_paciente: str) -> dict:
    row = _buscar_paciente(id_paciente)
    if row is None:
        return {"error": "Paciente no encontrado"}
    return _presentar_fila(row.to_dict())


def crear(datos: dict) -> dict:
    df = _extraer()
    doc = str(datos.get("documento", "")).strip()
    if doc and not df.empty and doc in df["documento"].astype(str).values:
        return {"error": "Ya existe un paciente con ese documento"}

    ahora = datetime.now(timezone.utc).isoformat()
    pac = {
        "id_paciente": str(uuid.uuid4()),
        "codigo_historia": _siguiente_codigo(df),
        "nombre": str(datos.get("nombre", "")).strip(),
        "apellido": str(datos.get("apellido", "")).strip(),
        "documento": doc,
        "fecha_nacimiento": str(datos.get("fecha_nacimiento", ""))[:10],
        "genero": str(datos.get("genero", "Femenino")),
        "telefono": str(datos.get("telefono", "")),
        "email": str(datos.get("email", "")).strip().lower(),
        "sede": str(datos.get("sede", "California")),
        "estado": "activo",
        "notas": str(datos.get("notas", "")),
        "encounter_origen": "",
        "creado_en": ahora,
        "actualizado_en": ahora,
    }
    _cargar(pd.concat([df, pd.DataFrame([pac])], ignore_index=True))
    pac["edad"] = _edad_desde_nacimiento(pac["fecha_nacimiento"])
    pac["nombre_completo"] = f"{pac['nombre']} {pac['apellido']}".strip()
    return {"mensaje": "Paciente registrado", "paciente": pac}


def actualizar(id_paciente: str, cambios: dict) -> dict:
    df = _extraer()
    idx = df.index[df["id_paciente"] == id_paciente].tolist()
    if not idx:
        return {"error": "Paciente no encontrado"}
    permitidos = {"nombre", "apellido", "documento", "fecha_nacimiento", "genero",
                  "telefono", "email", "sede", "estado", "notas"}
    for k, v in cambios.items():
        if k in permitidos:
            df.at[idx[0], k] = v
    df.at[idx[0], "actualizado_en"] = datetime.now(timezone.utc).isoformat()
    _cargar(df)
    return {"mensaje": "Paciente actualizado", "paciente": obtener(id_paciente)}


def eliminar(id_paciente: str) -> dict:
    df = _extraer()
    if id_paciente not in df["id_paciente"].values:
        return {"error": "Paciente no encontrado"}
    df.loc[df["id_paciente"] == id_paciente, "estado"] = "inactivo"
    df.loc[df["id_paciente"] == id_paciente, "actualizado_en"] = datetime.now(timezone.utc).isoformat()
    _cargar(df)
    return {"mensaje": "Paciente dado de baja", "id_paciente": id_paciente}


def consultas_paciente(id_paciente: str, limit: int = 50) -> dict:
    from servicios.registros_clinicos.RegistrosClinicosServicio import listar_por_paciente
    return listar_por_paciente(id_paciente, limit)


def _consultas_a_puntos(consultas: list) -> list:
    puntos = []
    for i, r in enumerate(consultas):
        fecha = str(r.get("created_at") or r.get("year") or i + 1)[:10]
        try:
            puntos.append({
                "fecha": fecha,
                "bmi": round(float(r.get("bmi") or 0), 2),
                "hba1c": round(float(r.get("hbA1c_level") or 0), 2),
                "glucosa": int(float(r.get("blood_glucose_level") or 0)),
                "diabetes": int(r.get("diabetes") or 0),
            })
        except (TypeError, ValueError):
            continue
    puntos.sort(key=lambda p: p["fecha"])
    return puntos


def _eventos_desde_consultas(consultas: list) -> list:
    eventos = []
    for r in consultas:
        diab = "Sí" if r.get("diabetes") == 1 else "No"
        eventos.append({
            "tipo": "consulta",
            "fecha": r.get("created_at") or str(r.get("year", "")),
            "titulo": "Consulta clínica",
            "detalle": (
                f"BMI {r.get('bmi', '—')} · HbA1c {r.get('hbA1c_level', '—')} · "
                f"Glucosa {r.get('blood_glucose_level', '—')} · Diabetes {diab}"
            ),
            "extra": {"encounter_id": r.get("encounter_id")},
        })
    return eventos


def _leer_hechos_prediccion() -> pd.DataFrame:
    path = "hechos/hechos_prediccion.parquet"
    try:
        st = get_cliente().stat_object(BUCKET_APP, path)
        key = (st.etag, st.last_modified, st.size)
        if _hp_cache["df"] is not None and _hp_cache["stat"] == key:
            return _hp_cache["df"]
        obj = get_cliente().get_object(BUCKET_APP, path)
        df = pd.read_parquet(io.BytesIO(obj.read()))
        _hp_cache["df"] = df
        _hp_cache["stat"] = key
        return df
    except Exception:
        return pd.DataFrame()


def _eventos_prediccion(consultas: list) -> list:
    eids = {int(c["encounter_id"]) for c in consultas if c.get("encounter_id") is not None}
    if not eids:
        return []
    hp = _leer_hechos_prediccion()
    if hp.empty or "encounter_id" not in hp.columns:
        return []
    sub = hp[hp["encounter_id"].astype(int).isin(eids)]
    eventos = []
    for _, row in sub.iterrows():
        prob = row.get("probabilidad", 0) or 0
        eventos.append({
            "tipo": "prediccion",
            "fecha": str(row.get("fecha_prediccion", "")),
            "titulo": "Predicción ML",
            "detalle": f"{row.get('diagnostico_estimado', '—')} ({round(float(prob)*100, 1)}%)",
            "extra": {},
        })
    return eventos


def detalle_paciente(
    id_paciente: str,
    consultas_limit: int = 25,
    timeline_limit: int = 30,
    evolucion_limit: int = 60,
) -> dict:
    """Una sola lectura de datos: paciente + consultas + timeline + evolución."""
    row = _buscar_paciente(id_paciente)
    if row is None:
        return {"error": "Paciente no encontrado"}
    pac = _presentar_fila(row.to_dict())

    from servicios.registros_clinicos.RegistrosClinicosServicio import listar_por_paciente
    need = max(consultas_limit, timeline_limit, evolucion_limit)
    cons_data = listar_por_paciente(id_paciente, need)
    consultas = cons_data.get("consultas", [])

    eventos = _eventos_desde_consultas(consultas[:timeline_limit])
    try:
        from servicios.citas.CitasServicio import listar as listar_citas
        for c in listar_citas(id_paciente=id_paciente, limit=timeline_limit).get("citas", []):
            eventos.append({
                "tipo": "cita",
                "fecha": f"{c.get('fecha', '')}T{c.get('hora', '00:00')}:00",
                "titulo": f"Cita — {c.get('estado', '').replace('_', ' ').title()}",
                "detalle": c.get("motivo", ""),
                "extra": c,
            })
    except Exception:
        pass
    eventos.extend(_eventos_prediccion(consultas[:50]))
    eventos.sort(key=lambda e: str(e.get("fecha", "")), reverse=True)

    return {
        "paciente": pac,
        "consultas": consultas[:consultas_limit],
        "total_consultas": cons_data.get("total", 0),
        "eventos": eventos[:timeline_limit],
        "puntos": _consultas_a_puntos(consultas[:evolucion_limit]),
    }


def resumen() -> dict:
    total = _total_parquet()
    if total == 0:
        return {"total": 0, "activos": 0, "inactivos": 0, "formato_legacy": False, "legacy_pendientes": 0}
    if _cache.get("resumen") and _cache.get("stat") == _stat_archivo():
        return _cache["resumen"]
    data = {
        "total": total,
        "activos": total,
        "inactivos": 0,
        "formato_legacy": False,
        "legacy_pendientes": 0,
    }
    _cache["resumen"] = data
    _cache["stat"] = _stat_archivo()
    return data


_NS_PACIENTE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _uuid_desde_encuentro(encounter_id: int) -> str:
    return str(uuid.uuid5(_NS_PACIENTE, f"diabcare-pac-{int(encounter_id)}"))


_NOMBRES_M = [
    "Carlos", "Juan", "Miguel", "Luis", "Pedro", "Jorge", "Andrés", "Diego",
    "Ricardo", "Fernando", "Alejandro", "Daniel", "Santiago", "Mateo", "Sebastián", "Tomás",
]
_NOMBRES_F = [
    "María", "Ana", "Carmen", "Laura", "Sofía", "Elena", "Lucía", "Patricia",
    "Valentina", "Camila", "Isabella", "Gabriela", "Daniela", "Paula", "Andrea", "Natalia",
]
_APELLIDOS = [
    "García", "Rodríguez", "Martínez", "López", "Hernández", "González", "Pérez", "Sánchez",
    "Ramírez", "Torres", "Flores", "Rivera", "Gómez", "Díaz", "Cruz", "Morales",
    "Reyes", "Gutiérrez", "Ortiz", "Ruiz", "Vargas", "Castillo", "Romero", "Herrera",
]


def _documento_desde_encounter(encounter_id: int) -> str:
    """Documento visible al usuario (no ID interno)."""
    s = f"{int(encounter_id):07d}"
    return f"CC {s[0]}.{s[1:4]}.{s[4:7]}"


def _encounter_desde_documento(doc: str) -> int | None:
    doc = str(doc or "").strip()
    if doc.startswith("DS-"):
        try:
            return int(doc.split("-", 1)[1])
        except ValueError:
            return None
    digits = "".join(c for c in doc if c.isdigit())
    if digits:
        try:
            return int(digits)
        except ValueError:
            return None
    return None


def _nombre_apellido(encounter_id: int, es_femenino: bool) -> tuple[str, str]:
    eid = int(encounter_id)
    pool = _NOMBRES_F if es_femenino else _NOMBRES_M
    nombre = pool[(eid * 17 + 3) % len(pool)]
    ap1 = _APELLIDOS[(eid * 31 + 7) % len(_APELLIDOS)]
    ap2 = _APELLIDOS[(eid * 43 + 11) % len(_APELLIDOS)]
    if ap1 == ap2:
        ap2 = _APELLIDOS[(eid * 43 + 13) % len(_APELLIDOS)]
    apellido = ap1 if eid % 4 == 0 else f"{ap1} {ap2}"
    return nombre, apellido


def _obtener_datos_dataset() -> pd.DataFrame:
    """Lee encuentros desde stage/ — 1 fila = 1 paciente (por encounter_id)."""
    from servicios.dataset.DatasetDwhServicio import _leer_stage_plano, _normalizar_plano

    plano = _normalizar_plano(_leer_stage_plano())
    if plano.empty:
        try:
            from servicios.registros_clinicos.RegistrosClinicosServicio import _extraer
            plano = _extraer()
        except Exception:
            plano = pd.DataFrame()

    if plano.empty:
        return pd.DataFrame()

    if "gender" not in plano.columns and "Gender" in plano.columns:
        plano = plano.rename(columns={"Gender": "gender", "Age": "age", "Location": "location"})

    if "gender" not in plano.columns or "age" not in plano.columns:
        return pd.DataFrame()

    if "encounter_id" not in plano.columns:
        plano.insert(0, "encounter_id", range(1, len(plano) + 1))

    plano = plano.drop(columns=["id_paciente", "paciente_nombre"], errors="ignore")
    plano = plano.dropna(subset=["encounter_id"])
    plano["encounter_id"] = plano["encounter_id"].astype(int)
    plano = plano.drop_duplicates(subset=["encounter_id"], keep="first").reset_index(drop=True)
    # Cada registro del dataset es un paciente distinto (perfil clínico coherente).
    plano["id_paciente"] = plano["encounter_id"]
    return plano


def _mapa_encuentros_existentes(pacientes_df: pd.DataFrame) -> dict[int, str]:
    out: dict[int, str] = {}
    if pacientes_df.empty:
        return out
    for _, p in pacientes_df.iterrows():
        eid = None
        if "encounter_origen" in p.index and pd.notna(p.get("encounter_origen")) and str(p.get("encounter_origen")).strip():
            try:
                eid = int(p["encounter_origen"])
            except (TypeError, ValueError):
                eid = None
        if eid is None:
            eid = _encounter_desde_documento(str(p.get("documento", "")))
        if eid is not None:
            out[int(eid)] = str(p["id_paciente"])
    return out


def _es_paciente_importado(row) -> bool:
    if "encounter_origen" in row.index and pd.notna(row.get("encounter_origen")) and str(row.get("encounter_origen")).strip():
        return True
    doc = str(row.get("documento", ""))
    return doc.startswith("DS-") or doc.startswith("CC ")


def _crear_pacientes_desde_filas(df: pd.DataFrame, ahora: str, anio: int) -> pd.DataFrame:
    """Genera expedientes en bloque: 1 fila del dataset → 1 paciente."""
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS)

    eids = df["encounter_id"].astype(int)
    generos = df["gender"].fillna("Femenino").astype(str)
    edades = df["age"].fillna(45).astype(float).clip(lower=1).astype(int)
    sedes = (
        df["location"].fillna("California").astype(str)
        if "location" in df.columns
        else pd.Series(["California"] * len(df), index=df.index)
    )
    fem = generos.str.lower().str.contains("fem", na=False)
    e = eids.to_numpy()
    nombres = []
    apellidos = []
    for i, eid in enumerate(e):
        nom, ape = _nombre_apellido(int(eid), bool(fem.iloc[i]))
        nombres.append(nom)
        apellidos.append(ape)

    return pd.DataFrame({
        "id_paciente": [_uuid_desde_encuentro(int(x)) for x in e],
        "codigo_historia": [f"HC-{int(x):06d}" for x in e],
        "nombre": nombres,
        "apellido": apellidos,
        "documento": [_documento_desde_encounter(int(x)) for x in e],
        "fecha_nacimiento": [f"{anio - int(edades.iloc[i])}-06-15" for i in range(len(e))],
        "genero": generos.values,
        "telefono": "",
        "email": [f"contacto.{int(x)}@paciente.diabcare.local" for x in e],
        "sede": sedes.values,
        "estado": "activo",
        "notas": "Expediente generado desde datos clínicos",
        "encounter_origen": eids.astype(int).tolist(),
        "creado_en": ahora,
        "actualizado_en": ahora,
    })


def _desvincular_encuentros(encounter_ids: set[int]) -> None:
    if not encounter_ids:
        return
    try:
        from servicios.registros_clinicos.RegistrosClinicosServicio import (
            _extraer as extraer_reg, _cargar as cargar_reg, invalidar_cache,
        )
        reg = extraer_reg()
        if reg.empty or "encounter_id" not in reg.columns:
            return
        mask = reg["encounter_id"].astype(int).isin(encounter_ids)
        if not mask.any():
            return
        reg.loc[mask, "id_paciente"] = ""
        reg.loc[mask, "paciente_nombre"] = ""
        cargar_reg(reg)
        invalidar_cache()
    except Exception:
        pass


def importar_desde_dataset(forzar: bool = False) -> dict:
    """
    Crea 1 expediente por fila del dataset (encounter_id) y vincula su consulta.
    Idempotente: encounter_origen vincula cada fila del dataset a un expediente.
    """
    datos = _obtener_datos_dataset()
    if datos.empty:
        return {"error": "No hay datos en MinIO. Use Dataset → Generador o Pipeline ELT primero."}

    total_encuentros = len(datos)
    pacientes_df = _extraer()
    if "encounter_origen" not in pacientes_df.columns:
        pacientes_df["encounter_origen"] = ""
    n_imp = int(pacientes_df.apply(_es_paciente_importado, axis=1).sum()) if not pacientes_df.empty else 0

    if forzar:
        eids = set(datos["encounter_id"].astype(int).tolist())
        _desvincular_encuentros(eids)
        if not pacientes_df.empty:
            mask_imp = pacientes_df.apply(_es_paciente_importado, axis=1)
            pacientes_df = pacientes_df[~mask_imp].copy()
            _cargar(pacientes_df)
        n_imp = 0

    if not forzar and n_imp > 0:
        legacy = _contar_legacy(pacientes_df)
        if legacy > 0:
            total_mig = 0
            vinc = 0
            while True:
                mig = migrar_formato_legacy()
                total_mig += mig.get("migrados", 0)
                vinc = mig.get("consultas_vinculadas", vinc)
                if not mig.get("formato_legacy"):
                    break
            return {
                "mensaje": mig.get("mensaje", "Expedientes actualizados"),
                "pacientes_total": n_imp,
                "pacientes_nuevos": 0,
                "migrados": total_mig,
                "consultas_vinculadas": vinc,
                "encuentros_dataset": total_encuentros,
            }
        if n_imp >= total_encuentros - 50:
            vinc = _sync_registros_desde_plano(datos) + _vincular_consultas(datos, _extraer())
            return {
                "mensaje": "Pacientes ya importados",
                "pacientes_total": n_imp,
                "pacientes_nuevos": 0,
                "consultas_vinculadas": vinc,
                "encuentros_dataset": total_encuentros,
            }
        return {
            "error": (
                f"Importación incompleta ({n_imp} pacientes vs {total_encuentros} registros). "
                "Use «Sincronizar datos» para reimportar."
            ),
            "pacientes_total": n_imp,
            "encuentros_dataset": total_encuentros,
            "requiere_forzar": True,
        }

    map_uuid = _mapa_encuentros_existentes(pacientes_df)
    faltantes = datos[~datos["encounter_id"].astype(int).isin(map_uuid.keys())].copy()

    ahora = datetime.now(timezone.utc).isoformat()
    anio = datetime.now().year
    nuevos_df = _crear_pacientes_desde_filas(faltantes, ahora, anio)

    if not nuevos_df.empty:
        pacientes_df = pd.concat([pacientes_df, nuevos_df], ignore_index=True)
        _cargar(pacientes_df)
        ids_doc = nuevos_df["encounter_origen"].astype(int)
        map_uuid.update(dict(zip(ids_doc, nuevos_df["id_paciente"].astype(str))))
    elif pacientes_df.empty:
        return {"error": "No se pudieron crear pacientes"}

    vinculadas = _sync_registros_desde_plano(datos)
    vinculadas += _vincular_consultas(datos, _extraer(), map_uuid)

    total_pac = len(_extraer())
    return {
        "mensaje": "Pacientes cargados (1 expediente por registro)",
        "pacientes_nuevos": len(nuevos_df),
        "pacientes_total": total_pac,
        "consultas_vinculadas": vinculadas,
        "encuentros_dataset": total_encuentros,
        "fuente": "minio_dataset",
    }


def _sync_registros_desde_plano(datos: pd.DataFrame) -> int:
    """Copia encuentros del dataset al archivo clínico si aún no existen (vectorizado)."""
    try:
        from servicios.registros_clinicos.RegistrosClinicosServicio import (
            _extraer as extraer_reg, _cargar as cargar_reg, invalidar_cache,
        )
        reg = extraer_reg()
        existentes = set(reg["encounter_id"].astype(int).tolist()) if not reg.empty and "encounter_id" in reg.columns else set()

        nuevos = datos[~datos["encounter_id"].astype(int).isin(existentes)].copy()
        if nuevos.empty:
            return 0

        ahora = datetime.now(timezone.utc).isoformat()
        anio = datetime.now().year
        filas = nuevos.copy()
        filas["encounter_id"] = filas["encounter_id"].astype(int)
        filas["year"] = filas["year"].fillna(anio).astype(int) if "year" in filas.columns else anio
        filas["gender"] = filas["gender"] if "gender" in filas.columns else "Femenino"
        filas["age"] = filas["age"].astype(float) if "age" in filas.columns else 45.0
        filas["location"] = filas["location"] if "location" in filas.columns else "California"
        for col, default in [
            ("hypertension", 0), ("heart_disease", 0), ("smoking_history", "nunca"),
            ("bmi", 0.0), ("hbA1c_level", 0.0), ("blood_glucose_level", 0), ("diabetes", 0),
        ]:
            if col not in filas.columns:
                filas[col] = default
        out = filas[[
            "encounter_id", "year", "gender", "age", "location",
            "hypertension", "heart_disease", "smoking_history",
            "bmi", "hbA1c_level", "blood_glucose_level", "diabetes",
        ]].copy()
        out["created_at"] = ahora
        out["id_paciente"] = out["encounter_id"].map(_uuid_desde_encuentro)
        out["paciente_nombre"] = ""
        reg = pd.concat([reg, out], ignore_index=True)
        cargar_reg(reg)
        invalidar_cache()
        return len(out)
    except Exception:
        return 0


def _vincular_consultas(
    datos: pd.DataFrame,
    pacientes_df: pd.DataFrame,
    map_uuid: dict[int, str] | None = None,
) -> int:
    try:
        from servicios.registros_clinicos.RegistrosClinicosServicio import (
            _extraer as extraer_reg, _cargar as cargar_reg, invalidar_cache,
        )
        reg = extraer_reg()
        if reg.empty or "encounter_id" not in reg.columns:
            return 0

        reg = reg.dropna(subset=["encounter_id"]).copy()
        reg["encounter_id"] = reg["encounter_id"].astype(int)
        if "id_paciente" not in reg.columns:
            reg["id_paciente"] = ""
        if "paciente_nombre" not in reg.columns:
            reg["paciente_nombre"] = ""

        if pacientes_df.empty:
            return 0

        if "encounter_origen" in pacientes_df.columns:
            lookup = pacientes_df[
                pacientes_df["encounter_origen"].notna()
                & (pacientes_df["encounter_origen"].astype(str).str.strip() != "")
            ].copy()
            if not lookup.empty:
                lookup["encounter_id"] = lookup["encounter_origen"].astype(int)
            else:
                lookup = pd.DataFrame()
        else:
            lookup = pd.DataFrame()

        if lookup.empty:
            lookup = pacientes_df[
                pacientes_df["documento"].astype(str).str.startswith(("DS-", "CC "))
            ].copy()
            if not lookup.empty:
                lookup["encounter_id"] = lookup["documento"].astype(str).map(_encounter_desde_documento)

        if lookup.empty:
            return 0

        lookup = lookup.dropna(subset=["encounter_id"]).copy()
        lookup["encounter_id"] = lookup["encounter_id"].astype(int)
        lookup["uid"] = lookup["id_paciente"].astype(str)
        lookup["paciente_nombre"] = (
            lookup["nombre"].fillna("").astype(str) + " " + lookup["apellido"].fillna("").astype(str)
        ).str.strip()
        lookup = lookup[["encounter_id", "uid", "paciente_nombre"]].rename(
            columns={"paciente_nombre": "nombre_vinculo"}
        )

        merged = reg.merge(lookup, on="encounter_id", how="left")
        sin_vinculo = merged["id_paciente"].astype(str).str.strip().isin(["", "nan", "None"])
        mask = sin_vinculo & merged["uid"].notna()
        vinculadas = int(mask.sum())
        if vinculadas == 0:
            return 0

        reg.loc[mask, "id_paciente"] = merged.loc[mask, "uid"].values
        reg.loc[mask, "paciente_nombre"] = merged.loc[mask, "nombre_vinculo"].fillna("").values
        cargar_reg(reg)
        invalidar_cache()
        return vinculadas
    except Exception:
        return 0


def timeline_paciente(id_paciente: str, limit: int = 80) -> dict:
    """Historia clínica unificada: citas, consultas y predicciones."""
    d = detalle_paciente(id_paciente, consultas_limit=limit, timeline_limit=limit)
    if d.get("error"):
        return d
    return {"paciente": d["paciente"], "eventos": d["eventos"], "total": len(d["eventos"])}


def evolucion_clinica(id_paciente: str, limit: int = 120) -> dict:
    """Series temporales de métricas clínicas para gráficos de evolución."""
    d = detalle_paciente(id_paciente, evolucion_limit=limit)
    if d.get("error"):
        return d
    return {"paciente": d["paciente"], "puntos": d["puntos"], "total": len(d["puntos"])}


def generar_expediente_pdf(id_paciente: str) -> bytes | None:
    """PDF con datos del paciente, citas y consultas."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    tl = timeline_paciente(id_paciente, limit=50)
    if tl.get("error"):
        return None
    pac = tl["paciente"]

    def _txt(v):
        return str(v).encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _txt("DiabCare — Expediente clínico"))
    pdf.ln(12)

    def linea(etq, val):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 6, _txt(etq), new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _txt(val), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    linea("Paciente:", pac.get("nombre_completo", ""))
    linea("Historia clínica:", pac.get("codigo_historia", ""))
    linea("Documento:", pac.get("documento", ""))
    linea("Edad / Genero:", f"{pac.get('edad', '-')} anos - {pac.get('genero', '')}")
    linea("Sede:", pac.get("sede", ""))
    linea("Estado:", pac.get("estado", "activo"))
    if pac.get("notas"):
        linea("Notas:", pac.get("notas"))

    pdf.ln(4)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _txt("Linea de tiempo clinica"))
    pdf.ln(10)

    for ev in tl.get("eventos", [])[:40]:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 9)
        titulo = f"[{ev.get('tipo', '').upper()}] {ev.get('titulo', '')} - {str(ev.get('fecha', ''))[:16]}"
        pdf.multi_cell(0, 5, _txt(titulo), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, _txt(ev.get("detalle", "")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 6, _txt(f"Generado {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"))
    return bytes(pdf.output())
