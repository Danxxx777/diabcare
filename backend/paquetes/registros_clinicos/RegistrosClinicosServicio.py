import io
import json
import random
import pandas as pd
from collections import Counter
from datetime import datetime
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
from paquetes.configuracion.ConfiguracionAjustes import MINIO_BUCKET, MINIO_STAGE_PATH
from paquetes.dataset.DatasetTraducciones import (
    GENERO_CANON,
    TABACO_MAP,
    aliases_genero,
    normalizar_genero,
    normalizar_tabaco,
    normalizar_raza,
    traducir_registro,
    RAZA_ES,
)

ARCHIVO_PRINCIPAL = f"{MINIO_STAGE_PATH}diabcare_registros.parquet"
# Debe ordenar DESPUÉS del canónico (fusionar aplica keep=last por encounter_id).
ARCHIVO_DELTA = f"{MINIO_STAGE_PATH}diabcare_registros_delta.parquet"
ARCHIVO_META = f"{MINIO_STAGE_PATH}.crud_meta.json"
STATS_SNAPSHOT = f"{MINIO_STAGE_PATH}.diabcare_estadisticas_v3.json"
RAZAS = ["race_AfricanAmerican", "race_Asian", "race_Caucasian", "race_Hispanic", "race_Other"]
EDAD_BINS = [0, 20, 30, 40, 50, 60, 70, 200]
EDAD_LABELS = ["<20", "20-30", "31-40", "41-50", "51-60", "61-70", "70+"]
BMI_BINS = [0, 18.5, 25, 30, 35, 100]
BMI_LABELS = ["<18.5", "18.5-24.9", "25-29.9", "30-34.9", "≥35"]
HBA_BINS = [0, 5.7, 6.5, 7, 8, 15]
HBA_LABELS = ["<5.7", "5.7-6.4", "6.5-6.9", "7-7.9", "≥8"]
GLC_BINS = [0, 100, 126, 200, 401]
GLC_LABELS = ["<100", "100-125", "126-199", "≥200"]
SCATTER_MAX = 600
STATS_COLS = [
    "diabetes", "gender", "smoking_history", "age", "bmi", "hbA1c_level",
    "blood_glucose_level", "hypertension", "heart_disease", "location", "year",
] + RAZAS
CHUNK_STATS = 250_000

_cache = {"df": None, "fp": None, "stats": None, "stats_fp": None, "calidad": None, "calidad_fp": None}

_GENERO_MAP: dict[str, str] = {}
for _canon, _aliases in GENERO_CANON.items():
    for _a in _aliases + [_canon]:
        _GENERO_MAP[str(_a).strip()] = _canon
        _GENERO_MAP[str(_a).strip().lower()] = _canon


def invalidar_cache():
    _cache["df"] = None
    _cache["fp"] = None
    _cache["stats"] = None
    _cache["stats_fp"] = None
    _cache["calidad"] = None
    _cache["calidad_fp"] = None
    # Snapshot de MinIO: borrar para que stats no resuciten con fingerprint viejo
    for snap in (
        STATS_SNAPSHOT,
        f"{MINIO_STAGE_PATH}.diabcare_estadisticas_v2.json",
        f"{MINIO_STAGE_PATH}.diabcare_estadisticas.json",
    ):
        try:
            get_cliente().remove_object(MINIO_BUCKET, snap)
        except Exception:
            pass


def _traducir_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "gender" in out.columns:
        out["gender"] = out["gender"].apply(normalizar_genero)
    if "smoking_history" in out.columns:
        out["smoking_history"] = out["smoking_history"].apply(normalizar_tabaco)
    return out


def _filtrar_genero(df: pd.DataFrame, genero: str) -> pd.DataFrame:
    vals = aliases_genero(genero)
    return df[df["gender"].isin(vals)]

def _listar_parquets():
    c = get_cliente()
    return sorted(
        [
            o for o in c.list_objects(MINIO_BUCKET, prefix=MINIO_STAGE_PATH, recursive=True)
            if o.object_name.endswith(".parquet")
        ],
        key=lambda o: o.object_name,
    )


def _fingerprint() -> str:
    parts = []
    for o in _listar_parquets():
        lm = o.last_modified.isoformat() if o.last_modified else ""
        parts.append(f"{o.object_name}:{o.size}:{lm}")
    return "|".join(parts)


def _iter_chunks(batch_size: int = CHUNK_STATS):
    import pyarrow.parquet as pq

    c = get_cliente()
    max_id = 0
    for o in _listar_parquets():
        obj = c.get_object(MINIO_BUCKET, o.object_name)
        pf = pq.ParquetFile(io.BytesIO(obj.read()))
        names = set(pf.schema_arrow.names)
        cols = [col for col in STATS_COLS if col in names]
        if "encounter_id" in names and "encounter_id" not in cols:
            cols = ["encounter_id"] + cols
        if not cols:
            continue
        shift = None
        file_max = max_id
        for batch in pf.iter_batches(batch_size=batch_size, columns=cols):
            chunk = batch.to_pandas()
            if chunk.empty:
                continue
            if "encounter_id" in chunk.columns:
                ids = pd.to_numeric(chunk["encounter_id"], errors="coerce")
                chunk = chunk.loc[ids.notna()].copy()
                if chunk.empty:
                    continue
                chunk["encounter_id"] = ids.loc[ids.notna()].astype("int64")
                if shift is None:
                    mn = int(chunk["encounter_id"].min())
                    if max_id > 0 and mn <= max_id:
                        shift = max_id + 1 - mn
                    else:
                        shift = 0
                if shift:
                    chunk["encounter_id"] = chunk["encounter_id"] + shift
                file_max = max(file_max, int(chunk["encounter_id"].max()))
            yield chunk
        max_id = max(max_id, file_max)


def _leer_snapshot(fp: str) -> dict | None:
    try:
        obj = get_cliente().get_object(MINIO_BUCKET, STATS_SNAPSHOT)
        data = json.loads(obj.read())
        if data.get("fp") == fp and isinstance(data.get("payload"), dict):
            return data["payload"]
    except Exception:
        pass
    return None


def _guardar_snapshot(fp: str, payload: dict) -> None:
    try:
        body = json.dumps({"fp": fp, "payload": payload}, ensure_ascii=False).encode("utf-8")
        get_cliente().put_object(MINIO_BUCKET, STATS_SNAPSHOT, io.BytesIO(body), len(body))
    except Exception:
        pass


def _extraer(force: bool = False) -> pd.DataFrame:
    from paquetes.dataset.DatasetServicio import fusionar_stage_dataframes

    fp = _fingerprint()
    if not fp:
        return pd.DataFrame()
    if not force and _cache["df"] is not None and _cache["fp"] == fp:
        return _cache["df"]

    try:
        c = get_cliente()
        dfs = []
        for obj in _listar_parquets():
            data = c.get_object(MINIO_BUCKET, obj.object_name)
            dfs.append(pd.read_parquet(io.BytesIO(data.read())))
        if not dfs:
            return pd.DataFrame()
        df = fusionar_stage_dataframes(dfs)
        if "encounter_id" not in df.columns:
            df.insert(0, "encounter_id", range(1, len(df) + 1))
        deletes = set(_leer_deletes())
        if deletes and "encounter_id" in df.columns:
            df = df[~pd.to_numeric(df["encounter_id"], errors="coerce").isin(deletes)].copy()
        _cache["df"] = df
        _cache["fp"] = fp
        _cache["stats"] = None
        _cache["stats_fp"] = None
        _cache["calidad"] = None
        _cache["calidad_fp"] = None
        _sync_meta_max(df)
        return df
    except Exception as e:
        print(f"[ELT] Error extrayendo: {e}")
        return pd.DataFrame()


def _leer_meta() -> dict:
    try:
        obj = get_cliente().get_object(MINIO_BUCKET, ARCHIVO_META)
        data = json.loads(obj.read())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _guardar_meta(meta: dict) -> None:
    try:
        body = json.dumps(meta, ensure_ascii=False).encode("utf-8")
        get_cliente().put_object(MINIO_BUCKET, ARCHIVO_META, io.BytesIO(body), len(body))
    except Exception as e:
        print(f"[ELT] Error meta CRUD: {e}")


def _leer_deletes() -> list[int]:
    raw = _leer_meta().get("deletes") or []
    out = []
    for x in raw:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            pass
    return out


def _sync_meta_max(df: pd.DataFrame) -> None:
    if df is None or df.empty or "encounter_id" not in df.columns:
        return
    try:
        mx = int(pd.to_numeric(df["encounter_id"], errors="coerce").max())
    except Exception:
        return
    meta = _leer_meta()
    if int(meta.get("max_encounter_id") or 0) >= mx:
        return
    meta["max_encounter_id"] = mx
    meta.setdefault("deletes", meta.get("deletes") or [])
    _guardar_meta(meta)


def _alloc_encounter_id() -> int:
    """Siguiente ID sin forzar lectura completa si hay caché o meta."""
    df = _cache.get("df")
    if df is not None and not df.empty and "encounter_id" in df.columns:
        try:
            return int(pd.to_numeric(df["encounter_id"], errors="coerce").max()) + 1
        except Exception:
            pass
    meta = _leer_meta()
    if meta.get("max_encounter_id"):
        return int(meta["max_encounter_id"]) + 1
    df = _extraer()
    if df.empty or "encounter_id" not in df.columns:
        return 1
    return int(pd.to_numeric(df["encounter_id"], errors="coerce").max()) + 1


def _leer_delta() -> pd.DataFrame:
    try:
        obj = get_cliente().get_object(MINIO_BUCKET, ARCHIVO_DELTA)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame()


def _escribir_delta(df: pd.DataFrame) -> bool:
    try:
        c = get_cliente()
        if df is None or df.empty:
            try:
                c.remove_object(MINIO_BUCKET, ARCHIVO_DELTA)
            except Exception:
                pass
            return True
        if "encounter_id" in df.columns:
            df = df.drop_duplicates(subset=["encounter_id"], keep="last")
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        c.put_object(MINIO_BUCKET, ARCHIVO_DELTA, buf, buf.getbuffer().nbytes)
        return True
    except Exception as e:
        print(f"[ELT] Error escribiendo delta: {e}")
        return False


def _upsert_delta_rows(rows: list[dict]) -> bool:
    if not rows:
        return True
    delta = _leer_delta()
    add = pd.DataFrame(rows)
    delta = add if delta.empty else pd.concat([delta, add], ignore_index=True)
    return _escribir_delta(delta)


def _cache_aplicar_upsert(rows: list[dict]) -> None:
    """Actualiza caché en memoria sin re-descargar MinIO."""
    if not rows:
        return
    df = _cache.get("df")
    if df is None:
        # Evitar caché parcial (1 fila) que haría listar devolver total=1
        _cache["fp"] = None
        return
    add = pd.DataFrame(rows)
    if df.empty:
        _cache["df"] = add.copy()
    else:
        ids = set(pd.to_numeric(add["encounter_id"], errors="coerce").dropna().astype("int64"))
        if ids and "encounter_id" in df.columns:
            mask = ~pd.to_numeric(df["encounter_id"], errors="coerce").isin(ids)
            df = df.loc[mask]
        _cache["df"] = pd.concat([df, add], ignore_index=True)
    _cache["fp"] = _fingerprint()
    _cache["stats"] = None
    _cache["stats_fp"] = None
    _cache["calidad"] = None
    _cache["calidad_fp"] = None


def _cache_aplicar_delete(encounter_id: int) -> None:
    df = _cache.get("df")
    if df is None:
        _cache["fp"] = None
        return
    if df.empty or "encounter_id" not in df.columns:
        return
    eid = int(encounter_id)
    _cache["df"] = df[pd.to_numeric(df["encounter_id"], errors="coerce") != eid].copy()
    _cache["fp"] = _fingerprint()
    _cache["stats"] = None
    _cache["stats_fp"] = None


def _cargar(df: pd.DataFrame, *, materializar: bool = False):
    """Reescribe el canónico (compactación). No usar en el hot-path del CRUD."""
    try:
        c = get_cliente()
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        c.put_object(MINIO_BUCKET, ARCHIVO_PRINCIPAL, buf, buf.getbuffer().nbytes)
        # Tras compactar: solo queda el canónico (+ meta). Evita re-fusión duplicada.
        for o in _listar_parquets():
            if o.object_name != ARCHIVO_PRINCIPAL:
                try:
                    c.remove_object(MINIO_BUCKET, o.object_name)
                except Exception:
                    pass
        meta = {"max_encounter_id": int(pd.to_numeric(df["encounter_id"], errors="coerce").max()) if not df.empty and "encounter_id" in df.columns else 0, "deletes": []}
        _guardar_meta(meta)
        _cache["df"] = df
        _cache["fp"] = _fingerprint()
        _cache["stats"] = None
        _cache["stats_fp"] = None
        _cache["calidad"] = None
        _cache["calidad_fp"] = None
        if materializar:
            try:
                import threading
                from paquetes.dataset.DatasetDwhServicio import materializar_dwh
                threading.Thread(target=materializar_dwh, daemon=True).start()
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"[ELT] Error cargando: {e}")
        return False


def _a_python(v):
    """Convierte escalares numpy/pandas a tipos Python JSON-seguros."""
    if v is None:
        return None
    try:
        import pandas as pd
        if pd.isna(v):
            return None
    except Exception:
        pass
    if hasattr(v, "item") and callable(v.item):
        try:
            return v.item()
        except Exception:
            pass
    return v


def _serializar_registro(reg: dict) -> dict:
    """Normaliza fecha, números y textos para la UI (sin floats sucios)."""
    out = {k: _a_python(v) for k, v in dict(reg).items()}

    fecha = (
        out.get("created_at")
        or out.get("encounter_date")
        or out.get("fecha")
        or ""
    )
    fecha = str(fecha).strip() if fecha not in (None, "") else ""
    if fecha and fecha not in ("nan", "None", "NaT", "NaN"):
        # ISO date o timestamp
        if len(fecha) >= 10 and fecha[4] == "-":
            out["fecha"] = fecha[:10]
        else:
            try:
                out["fecha"] = str(int(float(fecha)))
            except (TypeError, ValueError):
                out["fecha"] = fecha[:10] if len(fecha) >= 10 else fecha
    else:
        anio = out.get("year")
        try:
            if anio not in (None, "", "nan", "NaN"):
                out["fecha"] = str(int(float(anio)))
            else:
                out["fecha"] = ""
        except (TypeError, ValueError):
            out["fecha"] = ""

    if out.get("age") not in (None, ""):
        try:
            out["age"] = int(round(float(out["age"])))
        except (TypeError, ValueError):
            out["age"] = None

    for key, decimales in (
        ("bmi", 1),
        ("hbA1c_level", 1),
        ("blood_glucose_level", 0),
    ):
        if out.get(key) in (None, ""):
            continue
        try:
            val = float(out[key])
            out[key] = int(round(val)) if decimales == 0 else round(val, decimales)
        except (TypeError, ValueError):
            pass

    loc = out.get("location")
    if loc not in (None, ""):
        out["location"] = str(loc).strip().title()

    gen = out.get("gender")
    if gen not in (None, ""):
        g = str(gen).strip()
        out["gender"] = g[:1].upper() + g[1:] if g else g

    return out


def listar(limit: int = 50, offset: int = 0, filtros: dict = None) -> dict:
    df = _extraer()
    busqueda_rankeada = bool(filtros and filtros.get("q"))
    tiene_filtros = bool(filtros) and any(
        filtros.get(k) not in (None, "")
        for k in ("diabetes", "gender", "location", "age_min", "age_max", "q")
    )
    if filtros:
        if filtros.get("diabetes") is not None:
            df = df[df["diabetes"] == filtros["diabetes"]]
        if filtros.get("gender"):
            df = _filtrar_genero(df, filtros["gender"])
        if filtros.get("location"):
            df = df[df["location"].str.contains(str(filtros["location"]), case=False, na=False)]
        if filtros.get("age_min") is not None:
            df = df[df["age"] >= filtros["age_min"]]
        if filtros.get("age_max") is not None:
            df = df[df["age"] <= filtros["age_max"]]
        if filtros.get("q"):
            from nucleo.utilidades.Busqueda import rankear_dataframe
            campos = [c for c in (
                "paciente_nombre", "id_paciente", "location", "gender", "encounter_id",
            ) if c in df.columns]
            df = rankear_dataframe(df, str(filtros["q"]), campos)
    total = len(df)
    # Hot path: sin filtros, tomar cola (IDs ascendentes) sin sort de 1.3M filas
    if not busqueda_rankeada and not tiene_filtros and "encounter_id" in df.columns and total:
        end = total - offset
        start = max(0, end - limit)
        if end <= 0:
            chunk = df.iloc[0:0].copy()
        else:
            chunk = df.iloc[start:end].iloc[::-1].copy()
    else:
        if not busqueda_rankeada and "encounter_id" in df.columns and not df.empty:
            df = df.sort_values("encounter_id", ascending=False, kind="mergesort")
        chunk = df.iloc[offset:offset + limit].copy()
    chunk = _traducir_df(chunk)
    # Redondeo en DataFrame antes de serializar (evita float64 sucio en JSON)
    if "age" in chunk.columns:
        chunk["age"] = pd.to_numeric(chunk["age"], errors="coerce").round(0)
    if "bmi" in chunk.columns:
        chunk["bmi"] = pd.to_numeric(chunk["bmi"], errors="coerce").round(1)
    if "hbA1c_level" in chunk.columns:
        chunk["hbA1c_level"] = pd.to_numeric(chunk["hbA1c_level"], errors="coerce").round(1)
    if "blood_glucose_level" in chunk.columns:
        chunk["blood_glucose_level"] = pd.to_numeric(chunk["blood_glucose_level"], errors="coerce").round(0)
    if "year" in chunk.columns and "fecha" not in chunk.columns:
        yrs = pd.to_numeric(chunk["year"], errors="coerce")
        chunk["fecha"] = yrs.map(lambda y: str(int(y)) if pd.notna(y) else "")
    registros = [_serializar_registro(r) for r in chunk.where(pd.notnull(chunk), None).to_dict(orient="records")]
    ids = {str(r.get("id_paciente") or "") for r in registros if r.get("id_paciente")}
    if ids:
        try:
            from nucleo.utilidades.PacientesLookup import mapa_pacientes
            mapa = mapa_pacientes(ids)
            for r in registros:
                pid = str(r.get("id_paciente") or "")
                p = mapa.get(pid) or {}
                if p.get("nombre_completo") and not str(r.get("paciente_nombre") or "").strip():
                    r["paciente_nombre"] = p["nombre_completo"]
                r["tiene_foto"] = bool(p.get("tiene_foto"))
        except Exception:
            for r in registros:
                r.setdefault("tiene_foto", False)
    return {"total": total, "registros": registros}

def obtener(encounter_id: int) -> dict:
    df = _extraer()
    # Sin dataset en stage/, _extraer() devuelve un DataFrame sin columnas y el
    # filtro de abajo lanzaria KeyError -> 500 en vez de "no encontrado".
    if df.empty or "encounter_id" not in df.columns:
        return {"error": "Registro no encontrado"}
    fila = df[df["encounter_id"] == encounter_id]
    if fila.empty:
        return {"error": "Registro no encontrado"}
    return _serializar_registro(traducir_registro(fila.where(pd.notnull(fila), None).iloc[0].to_dict()))

def crear(datos: dict) -> dict:
    id_pac = str(datos.get("id_paciente") or "").strip()
    if not id_pac:
        return {"error": "Debe vincular un paciente del expediente (HCE) antes de guardar la consulta"}
    datos["id_paciente"] = id_pac
    try:
        from paquetes.clinico.pacientes.PacientesServicio import obtener as obtener_paciente
        p = obtener_paciente(id_pac)
        if "error" in p:
            return {"error": "Paciente no encontrado en el expediente (HCE)"}
        datos.setdefault("age", p.get("edad", datos.get("age", 45)))
        datos.setdefault("gender", p.get("genero", datos.get("gender", "Femenino")))
        datos.setdefault("location", p.get("sede", datos.get("location", "California")))
        datos["paciente_nombre"] = p.get("nombre_completo", "")
    except Exception:
        return {"error": "No se pudo validar el paciente del expediente"}

    nuevo_id = _alloc_encounter_id()
    datos["encounter_id"] = nuevo_id
    datos["created_at"] = datetime.utcnow().isoformat()
    datos.setdefault("year", datetime.utcnow().year)
    if "age" in datos and datos["age"] not in (None, ""):
        try:
            datos["age"] = int(round(float(datos["age"])))
        except (TypeError, ValueError):
            pass
    if datos.get("location"):
        datos["location"] = str(datos["location"]).strip().title()

    # Append-only: no reescribe los 1.3M del canónico
    if not _upsert_delta_rows([datos]):
        return {"error": "No se pudo guardar la consulta en almacenamiento (MinIO). Revisa que MinIO esté activo."}
    meta = _leer_meta()
    meta["max_encounter_id"] = max(int(meta.get("max_encounter_id") or 0), nuevo_id)
    meta.setdefault("deletes", meta.get("deletes") or [])
    _guardar_meta(meta)
    _cache_aplicar_upsert([datos])
    return {"mensaje": "Registro creado", "encounter_id": nuevo_id, "paciente_nombre": datos.get("paciente_nombre", "")}


def listar_por_paciente(id_paciente: str, limit: int = 50) -> dict:
    df = _extraer()
    if df.empty or "id_paciente" not in df.columns:
        return {"consultas": [], "total": 0}
    pid = str(id_paciente)
    sub = df[df["id_paciente"].astype(str) == pid]
    if sub.empty:
        return {"consultas": [], "total": 0}
    total = len(sub)
    if total > 1:
        sub = sub.sort_values("encounter_id", ascending=False)
    rows = sub.head(limit).fillna("").to_dict(orient="records")
    return {"consultas": [_serializar_registro(traducir_registro(r)) for r in rows], "total": total}

def actualizar(encounter_id: int, cambios: dict) -> dict:
    df = _extraer()
    idx = df.index[df["encounter_id"] == encounter_id].tolist()
    if not idx:
        return {"error": "Registro no encontrado"}
    if "age" in cambios and cambios["age"] not in (None, ""):
        try:
            cambios["age"] = int(round(float(cambios["age"])))
        except (TypeError, ValueError):
            pass
    if cambios.get("location"):
        cambios["location"] = str(cambios["location"]).strip().title()
    id_pac = str(cambios.get("id_paciente") or "").strip()
    if id_pac:
        try:
            from paquetes.clinico.pacientes.PacientesServicio import obtener as obtener_paciente
            p = obtener_paciente(id_pac)
            if "error" not in p:
                cambios["id_paciente"] = id_pac
                cambios["paciente_nombre"] = p.get("nombre_completo", "")
        except Exception:
            pass
    fila = df.loc[idx[0]].to_dict()
    fila.update(cambios)
    fila["encounter_id"] = int(encounter_id)
    if not _upsert_delta_rows([fila]):
        return {"error": "No se pudo actualizar la consulta en almacenamiento (MinIO)."}
    _cache_aplicar_upsert([fila])
    return {"mensaje": "Registro actualizado", "encounter_id": encounter_id}

def eliminar(encounter_id: int) -> dict:
    eid = int(encounter_id)
    df = _extraer()
    if df.empty or "encounter_id" not in df.columns:
        return {"error": "Registro no encontrado"}
    if not (pd.to_numeric(df["encounter_id"], errors="coerce") == eid).any():
        return {"error": "Registro no encontrado"}
    meta = _leer_meta()
    deletes = set(_leer_deletes())
    deletes.add(eid)
    meta["deletes"] = sorted(deletes)
    if meta.get("max_encounter_id") is None and not df.empty:
        meta["max_encounter_id"] = int(pd.to_numeric(df["encounter_id"], errors="coerce").max())
    _guardar_meta(meta)
    # Quitar del delta si estaba ahí (evita resucitar al fusionar)
    delta = _leer_delta()
    if not delta.empty and "encounter_id" in delta.columns:
        delta2 = delta[pd.to_numeric(delta["encounter_id"], errors="coerce") != eid]
        if len(delta2) != len(delta):
            _escribir_delta(delta2)
    _cache_aplicar_delete(eid)
    return {"mensaje": "Registro eliminado", "encounter_id": encounter_id}

def _hist_bins(values, mask_con, mask_sin, bins, labels, hist: dict) -> None:
    cats = pd.cut(values, bins=bins, labels=labels, right=False)
    for lbl in labels:
        m = cats == lbl
        hist[lbl]["con"] += int((m & mask_con).sum())
        hist[lbl]["sin"] += int((m & mask_sin).sum())


def _pct(con: int, total: int) -> float:
    return round(con / total * 100, 1) if total else 0.0


def _calc_estadisticas_incremental() -> dict:
    total = con = sin = 0
    bmi_con = bmi_sin = hba_con = hba_sin = glc_con = glc_sin = 0.0
    genero_c: Counter = Counter()
    genero_stats: dict = {}
    ubic_c: Counter = Counter()
    ubic_stats: dict = {}
    tabaco: dict = {}
    raza = {normalizar_raza(r): {"con_diabetes": 0, "sin_diabetes": 0} for r in RAZAS}
    edad = {lbl: {"sin_diabetes": 0, "con_diabetes": 0} for lbl in EDAD_LABELS}
    hist_bmi = {l: {"con": 0, "sin": 0} for l in BMI_LABELS}
    hist_hba = {l: {"con": 0, "sin": 0} for l in HBA_LABELS}
    hist_glc = {l: {"con": 0, "sin": 0} for l in GLC_LABELS}
    scatter: list = []
    scatter_seen = 0
    comorb = {
        "hipertension": {
            "con_diabetes_con": 0, "con_diabetes_sin": 0,
            "sin_diabetes_con": 0, "sin_diabetes_sin": 0,
        },
        "cardiopatia": {
            "con_diabetes_con": 0, "con_diabetes_sin": 0,
            "sin_diabetes_con": 0, "sin_diabetes_sin": 0,
        },
    }
    year_acc: dict[int, list[int]] = {}

    for chunk in _iter_chunks():
        if chunk.empty:
            continue

        if "encounter_id" in chunk.columns:
            chunk = chunk.dropna(subset=["encounter_id"]).copy()
            chunk["encounter_id"] = chunk["encounter_id"].astype(int)

        diab = chunk["diabetes"].fillna(0).astype(int) if "diabetes" in chunk.columns else pd.Series(0, index=chunk.index)
        mask_con = diab == 1
        mask_sin = ~mask_con
        total += len(chunk)
        con += int(mask_con.sum())
        sin += int(mask_sin.sum())

        if "bmi" in chunk.columns:
            bmi_con += float(chunk.loc[mask_con, "bmi"].sum())
            bmi_sin += float(chunk.loc[mask_sin, "bmi"].sum())
            _hist_bins(chunk["bmi"], mask_con, mask_sin, BMI_BINS, BMI_LABELS, hist_bmi)
        if "hbA1c_level" in chunk.columns:
            hba_con += float(chunk.loc[mask_con, "hbA1c_level"].sum())
            hba_sin += float(chunk.loc[mask_sin, "hbA1c_level"].sum())
            _hist_bins(chunk["hbA1c_level"], mask_con, mask_sin, HBA_BINS, HBA_LABELS, hist_hba)
        if "blood_glucose_level" in chunk.columns:
            glc_con += float(chunk.loc[mask_con, "blood_glucose_level"].sum())
            glc_sin += float(chunk.loc[mask_sin, "blood_glucose_level"].sum())
            _hist_bins(chunk["blood_glucose_level"], mask_con, mask_sin, GLC_BINS, GLC_LABELS, hist_glc)

        if "bmi" in chunk.columns and "hbA1c_level" in chunk.columns:
            sample = chunk.loc[mask_con | mask_sin, ["bmi", "hbA1c_level", "diabetes"]].dropna()
            if len(sample) > 80:
                sample = sample.sample(n=80, random_state=42)
            for _, row in sample.iterrows():
                scatter_seen += 1
                point = {
                    "bmi": round(float(row["bmi"]), 2),
                    "hba1c": round(float(row["hbA1c_level"]), 2),
                    "diabetes": int(row["diabetes"]),
                }
                if len(scatter) < SCATTER_MAX:
                    scatter.append(point)
                else:
                    j = random.randint(0, scatter_seen - 1)
                    if j < SCATTER_MAX:
                        scatter[j] = point

        if "gender" in chunk.columns:
            g = chunk["gender"].astype(str).str.strip().map(
                lambda x: _GENERO_MAP.get(x, _GENERO_MAP.get(x.lower(), x))
            )
            genero_c.update(g.value_counts().to_dict())
            tmp = chunk.assign(_g=g)
            for gv, grp in tmp.groupby("_g", observed=True):
                key = str(gv)
                if key not in genero_stats:
                    genero_stats[key] = {"total": 0, "con": 0, "sin": 0}
                genero_stats[key]["total"] += len(grp)
                genero_stats[key]["con"] += int((grp["diabetes"] == 1).sum())
                genero_stats[key]["sin"] += int((grp["diabetes"] == 0).sum())

        if "location" in chunk.columns:
            ubic_c.update(chunk["location"].dropna().astype(str).value_counts().to_dict())
            tmp = chunk.assign(_loc=chunk["location"].astype(str))
            for loc, grp in tmp.groupby("_loc", observed=True):
                if loc not in ubic_stats:
                    ubic_stats[loc] = {"total": 0, "con": 0, "sin": 0}
                ubic_stats[loc]["total"] += len(grp)
                ubic_stats[loc]["con"] += int((grp["diabetes"] == 1).sum())
                ubic_stats[loc]["sin"] += int((grp["diabetes"] == 0).sum())

        if "smoking_history" in chunk.columns:
            sm = chunk["smoking_history"].astype(str).str.strip().replace(TABACO_MAP)
            tmp = chunk.assign(_tab=sm)
            for clave, grp in tmp.groupby("_tab", observed=True):
                key = str(clave)
                if key not in tabaco:
                    tabaco[key] = {"con_diabetes": 0, "sin_diabetes": 0, "prevalencia": 0}
                tabaco[key]["con_diabetes"] += int((grp["diabetes"] == 1).sum())
                tabaco[key]["sin_diabetes"] += int((grp["diabetes"] == 0).sum())

        if "age" in chunk.columns:
            rangos = pd.cut(chunk["age"], bins=EDAD_BINS, labels=EDAD_LABELS, right=True)
            tmp = chunk.assign(rango=rangos)
            for lbl in EDAD_LABELS:
                sub = tmp[tmp["rango"] == lbl]
                if sub.empty:
                    continue
                edad[lbl]["con_diabetes"] += int((sub["diabetes"] == 1).sum())
                edad[lbl]["sin_diabetes"] += int((sub["diabetes"] == 0).sum())

        for r in RAZAS:
            if r not in chunk.columns:
                continue
            rk = normalizar_raza(r)
            raza[rk]["con_diabetes"] += int(chunk.loc[mask_con, r].sum())
            raza[rk]["sin_diabetes"] += int(chunk.loc[mask_sin, r].sum())

        if "hypertension" in chunk.columns:
            h = chunk["hypertension"].fillna(0).astype(int)
            comorb["hipertension"]["con_diabetes_con"] += int(((diab == 1) & (h == 1)).sum())
            comorb["hipertension"]["con_diabetes_sin"] += int(((diab == 1) & (h == 0)).sum())
            comorb["hipertension"]["sin_diabetes_con"] += int(((diab == 0) & (h == 1)).sum())
            comorb["hipertension"]["sin_diabetes_sin"] += int(((diab == 0) & (h == 0)).sum())

        if "heart_disease" in chunk.columns:
            hd = chunk["heart_disease"].fillna(0).astype(int)
            comorb["cardiopatia"]["con_diabetes_con"] += int(((diab == 1) & (hd == 1)).sum())
            comorb["cardiopatia"]["con_diabetes_sin"] += int(((diab == 1) & (hd == 0)).sum())
            comorb["cardiopatia"]["sin_diabetes_con"] += int(((diab == 0) & (hd == 1)).sum())
            comorb["cardiopatia"]["sin_diabetes_sin"] += int(((diab == 0) & (hd == 0)).sum())

        if "year" in chunk.columns:
            for yr, grp in chunk.groupby("year", observed=True):
                yi = int(yr)
                if yi not in year_acc:
                    year_acc[yi] = [0, 0]
                year_acc[yi][0] += len(grp)
                year_acc[yi][1] += int((grp["diabetes"] == 1).sum())

    if total == 0:
        return {"total": 0}

    for key, v in tabaco.items():
        t = v["con_diabetes"] + v["sin_diabetes"]
        v["prevalencia"] = _pct(v["con_diabetes"], t)

    prevalencia_edad = {
        lbl: _pct(edad[lbl]["con_diabetes"], edad[lbl]["con_diabetes"] + edad[lbl]["sin_diabetes"])
        for lbl in EDAD_LABELS
    }

    genero_prev = {
        k: {**v, "prevalencia": _pct(v["con"], v["total"])}
        for k, v in genero_stats.items()
    }

    top_ubic = sorted(ubic_stats.items(), key=lambda x: x[1]["total"], reverse=True)[:10]
    ubicaciones = {k: v["total"] for k, v in top_ubic}
    ubicaciones_prev = {
        k: {"total": v["total"], "prevalencia": _pct(v["con"], v["total"])}
        for k, v in top_ubic
    }

    razas_prev = {
        k: {
            **v,
            "prevalencia": _pct(v["con_diabetes"], v["con_diabetes"] + v["sin_diabetes"]),
        }
        for k, v in raza.items()
    }

    h = comorb["hipertension"]
    c = comorb["cardiopatia"]
    comorb_prev = {
        "hipertension": {
            "con_diabetes": _pct(h["con_diabetes_con"], h["con_diabetes_con"] + h["con_diabetes_sin"]),
            "sin_diabetes": _pct(h["sin_diabetes_con"], h["sin_diabetes_con"] + h["sin_diabetes_sin"]),
        },
        "cardiopatia": {
            "con_diabetes": _pct(c["con_diabetes_con"], c["con_diabetes_con"] + c["con_diabetes_sin"]),
            "sin_diabetes": _pct(c["sin_diabetes_con"], c["sin_diabetes_con"] + c["sin_diabetes_sin"]),
        },
    }

    tendencia = []
    for y, v in sorted(year_acc.items()):
        t, d = v[0], v[1]
        tendencia.append({"year": y, "total": t, "con_diabetes": d, "prevalencia": _pct(d, t)})

    return {
        "total": total,
        "con_diabetes": con,
        "sin_diabetes": sin,
        "genero": dict(genero_c),
        "genero_detalle": genero_prev,
        "tabaquismo": tabaco,
        "razas": raza,
        "razas_prevalencia": razas_prev,
        "edad": edad,
        "prevalencia_edad": prevalencia_edad,
        "histogramas": {"bmi": hist_bmi, "hba1c": hist_hba, "glucosa": hist_glc},
        "scatter_muestra": scatter,
        "promedios": {
            "bmi": {
                "con": round(bmi_con / con, 2) if con else 0,
                "sin": round(bmi_sin / sin, 2) if sin else 0,
            },
            "hba1c": {
                "con": round(hba_con / con, 2) if con else 0,
                "sin": round(hba_sin / sin, 2) if sin else 0,
            },
            "glucosa": {
                "con": round(glc_con / con, 1) if con else 0,
                "sin": round(glc_sin / sin, 1) if sin else 0,
            },
        },
        "comorbilidades": comorb,
        "comorbilidades_prevalencia": comorb_prev,
        "ubicaciones": ubicaciones,
        "ubicaciones_prevalencia": ubicaciones_prev,
        "tendencia": tendencia,
    }


def estadisticas() -> dict:
    fp = _fingerprint()
    if not fp:
        return {"total": 0}

    if _cache["stats"] is not None and _cache["stats_fp"] == fp:
        return _cache["stats"]

    snap = _leer_snapshot(fp)
    if snap is not None:
        _cache["stats"] = snap
        _cache["stats_fp"] = fp
        return snap

    result = _calc_estadisticas_incremental()
    _cache["stats"] = result
    _cache["stats_fp"] = fp
    if result.get("total", 0) > 0:
        _guardar_snapshot(fp, result)
    return result


def calidad_diabetes() -> dict:
    """
    Indicadores de control y riesgo en la cohorte con diabetes.
    Pensado para el rol analista (calidad clínica DM, sin PHI).
    """
    fp = _fingerprint()
    if not fp:
        return {"total_registros": 0, "con_diabetes": 0}

    if _cache.get("calidad") is not None and _cache.get("calidad_fp") == fp:
        return _cache["calidad"]

    df = _extraer()
    if df.empty or "diabetes" not in df.columns:
        out = {"total_registros": 0, "con_diabetes": 0}
        _cache["calidad"] = out
        _cache["calidad_fp"] = fp
        return out

    total = int(len(df))
    mask_dm = df["diabetes"].fillna(0).astype(int) == 1
    dm = df.loc[mask_dm].copy()
    n = int(len(dm))
    prevalencia = _pct(n, total)

    def _num(series):
        return pd.to_numeric(series, errors="coerce")

    hba = _num(dm["hbA1c_level"]) if "hbA1c_level" in dm.columns else pd.Series(dtype=float)
    glc = _num(dm["blood_glucose_level"]) if "blood_glucose_level" in dm.columns else pd.Series(dtype=float)
    bmi = _num(dm["bmi"]) if "bmi" in dm.columns else pd.Series(dtype=float)
    age = _num(dm["age"]) if "age" in dm.columns else pd.Series(dtype=float)

    hba_ok = hba.notna()
    n_hba = int(hba_ok.sum())
    control = int(((hba < 7) & hba_ok).sum())
    suboptimo = int(((hba >= 7) & (hba < 9) & hba_ok).sum())
    descontrol = int(((hba >= 9) & hba_ok).sum())

    glc_ok = glc.notna()
    n_glc = int(glc_ok.sum())
    glc_alta = int(((glc >= 180) & glc_ok).sum())
    glc_critica = int(((glc >= 250) & glc_ok).sum())

    bmi_ok = bmi.notna()
    n_bmi = int(bmi_ok.sum())
    obesidad = int(((bmi >= 30) & bmi_ok).sum())

    hiper = pd.Series(0, index=dm.index)
    cardio = pd.Series(0, index=dm.index)
    if "hypertension" in dm.columns:
        hiper = dm["hypertension"].fillna(0).astype(int)
    if "heart_disease" in dm.columns:
        cardio = dm["heart_disease"].fillna(0).astype(int)
    n_hiper = int((hiper == 1).sum())
    n_cardio = int((cardio == 1).sum())
    n_ambas = int(((hiper == 1) & (cardio == 1)).sum())

    # Estrato de riesgo clínico (prioridad: alto > medio > controlado)
    riesgo_alto = (
        ((hba >= 9) & hba_ok)
        | ((glc >= 250) & glc_ok)
        | ((hiper == 1) & (cardio == 1))
    )
    riesgo_medio = (
        ~riesgo_alto
        & (
            ((hba >= 7) & (hba < 9) & hba_ok)
            | ((glc >= 180) & (glc < 250) & glc_ok)
            | (hiper == 1)
            | (cardio == 1)
        )
    )
    riesgo_bajo = ~riesgo_alto & ~riesgo_medio
    n_alto = int(riesgo_alto.sum())
    n_medio = int(riesgo_medio.sum())
    n_bajo = int(riesgo_bajo.sum())

    # Descontrol HbA1c por grupo de edad
    por_edad = []
    if n and age.notna().any() and n_hba:
        cats = pd.cut(age, bins=EDAD_BINS, labels=EDAD_LABELS, right=False)
        for lbl in EDAD_LABELS:
            m = cats == lbl
            nn = int(m.sum())
            if not nn:
                continue
            dh = int(((hba >= 9) & hba_ok & m).sum())
            por_edad.append({
                "grupo": lbl,
                "con_diabetes": nn,
                "descontrol_hba1c": dh,
                "pct_descontrol": _pct(dh, int((m & hba_ok).sum()) or nn),
            })

    # Sedes con mayor % descontrol (top 8)
    por_sede = []
    if n and "location" in dm.columns and n_hba:
        loc = dm["location"].fillna("").astype(str).str.strip().str.title()
        for sede, idx in loc.groupby(loc).groups.items():
            if not sede or sede.lower() in ("", "nan", "none"):
                continue
            sub = dm.loc[idx]
            h = _num(sub["hbA1c_level"]) if "hbA1c_level" in sub.columns else pd.Series(dtype=float)
            ok = h.notna()
            nn = int(ok.sum())
            if nn < 5:
                continue
            dh = int(((h >= 9) & ok).sum())
            por_sede.append({
                "sede": sede[:40],
                "con_diabetes": int(len(sub)),
                "con_hba1c": nn,
                "descontrol_hba1c": dh,
                "pct_descontrol": _pct(dh, nn),
            })
        por_sede.sort(key=lambda x: (-x["pct_descontrol"], -x["con_diabetes"]))
        por_sede = por_sede[:8]

    out = {
        "total_registros": total,
        "con_diabetes": n,
        "sin_diabetes": total - n,
        "prevalencia_pct": prevalencia,
        "control_hba1c": {
            "con_dato": n_hba,
            "controlado_lt7": control,
            "suboptimo_7_9": suboptimo,
            "descontrol_gte9": descontrol,
            "pct_controlado": _pct(control, n_hba),
            "pct_suboptimo": _pct(suboptimo, n_hba),
            "pct_descontrol": _pct(descontrol, n_hba),
            "promedio": round(float(hba.mean()), 2) if n_hba else None,
        },
        "glucosa": {
            "con_dato": n_glc,
            "alta_gte180": glc_alta,
            "critica_gte250": glc_critica,
            "pct_alta": _pct(glc_alta, n_glc),
            "pct_critica": _pct(glc_critica, n_glc),
            "promedio": round(float(glc.mean()), 1) if n_glc else None,
        },
        "obesidad": {
            "con_dato": n_bmi,
            "bmi_gte30": obesidad,
            "pct_obesidad": _pct(obesidad, n_bmi),
            "promedio_bmi": round(float(bmi.mean()), 1) if n_bmi else None,
        },
        "comorbilidades_en_dm": {
            "hipertension": n_hiper,
            "cardiopatia": n_cardio,
            "ambas": n_ambas,
            "pct_hipertension": _pct(n_hiper, n),
            "pct_cardiopatia": _pct(n_cardio, n),
            "pct_ambas": _pct(n_ambas, n),
        },
        "riesgo": {
            "alto": n_alto,
            "medio": n_medio,
            "controlado": n_bajo,
            "pct_alto": _pct(n_alto, n),
            "pct_medio": _pct(n_medio, n),
            "pct_controlado": _pct(n_bajo, n),
        },
        "descontrol_por_edad": por_edad,
        "sedes_descontrol": por_sede,
        "recomendaciones": _recomendaciones_analista(
            n, n_hba, control, descontrol, glc_critica, n_ambas, n_alto
        ),
    }
    _cache["calidad"] = out
    _cache["calidad_fp"] = fp
    return out


def _recomendaciones_analista(
    n_dm: int,
    n_hba: int,
    control: int,
    descontrol: int,
    glc_critica: int,
    ambas_comorb: int,
    riesgo_alto: int,
) -> list[str]:
    tips = []
    if not n_dm:
        return ["Sin cohorte diabética en el dataset. Genere o materialice datos clínicos."]
    if n_hba and _pct(descontrol, n_hba) >= 20:
        tips.append(
            "Alto % con HbA1c ≥ 9%: priorice reporte de descontrol y revisión de sedes críticas."
        )
    if n_hba and _pct(control, n_hba) < 40:
        tips.append(
            "Control glucémico (HbA1c < 7%) bajo: contraste con predicción ML y reentrenar si el modelo envejeció."
        )
    if glc_critica:
        tips.append(
            f"{glc_critica} registros DM con glucosa ≥ 250: útil para alertas y cohortes de riesgo en reportes PDF."
        )
    if ambas_comorb:
        tips.append(
            f"{ambas_comorb} con hipertensión + cardiopatía: cohorte cardiovascular-diabetes para BI."
        )
    if riesgo_alto and _pct(riesgo_alto, n_dm) >= 25:
        tips.append(
            "≥25% de la cohorte DM en riesgo alto: eleve el hallazgo al dashboard ejecutivo y a notificaciones."
        )
    if not tips:
        tips.append(
            "Cohorte estable: genere reporte PDF de prevalencia y valide el modelo ML con métricas actuales."
        )
    return tips


def buscar(filtros: dict) -> dict:
    df = _extraer()
    if filtros.get("diabetes") is not None:
        df = df[df["diabetes"] == filtros["diabetes"]]
    if filtros.get("gender"):
        df = _filtrar_genero(df, filtros["gender"])
    if filtros.get("location"):
        df = df[df["location"].str.contains(filtros["location"], case=False, na=False)]
    if filtros.get("age_min"):
        df = df[df["age"] >= filtros["age_min"]]
    if filtros.get("age_max"):
        df = df[df["age"] <= filtros["age_max"]]
    return listar(limit=100, offset=0, filtros={k: v for k, v in filtros.items() if v is not None})