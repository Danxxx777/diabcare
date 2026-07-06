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
STATS_SNAPSHOT = f"{MINIO_STAGE_PATH}.diabcare_estadisticas_v2.json"
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

_cache = {"df": None, "fp": None, "stats": None, "stats_fp": None}

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
    try:
        get_cliente().remove_object(MINIO_BUCKET, STATS_SNAPSHOT)
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
    for o in _listar_parquets():
        obj = c.get_object(MINIO_BUCKET, o.object_name)
        pf = pq.ParquetFile(io.BytesIO(obj.read()))
        names = set(pf.schema_arrow.names)
        cols = [col for col in STATS_COLS if col in names]
        if "encounter_id" in names and "encounter_id" not in cols:
            cols = ["encounter_id"] + cols
        if not cols:
            continue
        for batch in pf.iter_batches(batch_size=batch_size, columns=cols):
            yield batch.to_pandas()


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
        df = pd.concat(dfs, ignore_index=True)
        if "encounter_id" in df.columns:
            df = df.drop_duplicates(subset=["encounter_id"], keep="last")
        if "encounter_id" not in df.columns:
            df.insert(0, "encounter_id", range(1, len(df) + 1))
        _cache["df"] = df
        _cache["fp"] = fp
        _cache["stats"] = None
        _cache["stats_fp"] = None
        return df
    except Exception as e:
        print(f"[ELT] Error extrayendo: {e}")
        return pd.DataFrame()

def _cargar(df: pd.DataFrame):
    try:
        c = get_cliente()
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        c.put_object(MINIO_BUCKET, ARCHIVO_PRINCIPAL, buf, buf.getbuffer().nbytes)
        _cache["df"] = df.copy()
        _cache["fp"] = _fingerprint()
        _cache["stats"] = None
        _cache["stats_fp"] = None
        try:
            from paquetes.dataset.DatasetDwhServicio import materializar_dwh
            materializar_dwh()
        except Exception:
            pass
        try:
            from paquetes.notificaciones.NotificacionesServicio import evaluar_alertas_clinicas
            evaluar_alertas_clinicas()
        except Exception:
            pass
    except Exception as e:
        print(f"[ELT] Error cargando: {e}")

def listar(limit: int = 50, offset: int = 0, filtros: dict = None) -> dict:
    df = _extraer()
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
            ql = str(filtros["q"]).lower().strip()
            if "paciente_nombre" in df.columns:
                df = df[df["paciente_nombre"].astype(str).str.lower().str.contains(ql, na=False)]
            else:
                df = df.iloc[0:0]
    total = len(df)
    chunk = _traducir_df(df.iloc[offset:offset + limit])
    return {"total": total, "registros": chunk.fillna("").to_dict(orient="records")}

def obtener(encounter_id: int) -> dict:
    df = _extraer()
    fila = df[df["encounter_id"] == encounter_id]
    if fila.empty:
        return {"error": "Registro no encontrado"}
    return traducir_registro(fila.fillna("").iloc[0].to_dict())

def crear(datos: dict) -> dict:
    df = _extraer()
    nuevo_id = int(df["encounter_id"].max()) + 1 if not df.empty else 1
    datos["encounter_id"] = nuevo_id
    datos["created_at"] = datetime.utcnow().isoformat()
    if "id_paciente" not in datos:
        datos["id_paciente"] = datos.get("id_paciente") or ""
    if datos.get("id_paciente"):
        try:
            from paquetes.clinico.pacientes.PacientesServicio import obtener as obtener_paciente
            p = obtener_paciente(str(datos["id_paciente"]))
            if "error" not in p:
                datos.setdefault("age", p.get("edad", datos.get("age", 45)))
                datos.setdefault("gender", p.get("genero", datos.get("gender", "Femenino")))
                datos.setdefault("location", p.get("sede", datos.get("location", "California")))
                datos["paciente_nombre"] = p.get("nombre_completo", "")
        except Exception:
            pass
    nuevo_df = pd.concat([df, pd.DataFrame([datos])], ignore_index=True)
    _cargar(nuevo_df)
    invalidar_cache()
    try:
        from paquetes.dataset.DatasetDwhServicio import materializar_dwh
        materializar_dwh()
    except Exception:
        pass
    return {"mensaje": "Registro creado", "encounter_id": nuevo_id}


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
    return {"consultas": [traducir_registro(r) for r in rows], "total": total}

def actualizar(encounter_id: int, cambios: dict) -> dict:
    df = _extraer()
    idx = df.index[df["encounter_id"] == encounter_id].tolist()
    if not idx:
        return {"error": "Registro no encontrado"}
    for k, v in cambios.items():
        df.at[idx[0], k] = v
    _cargar(df)
    return {"mensaje": "Registro actualizado", "encounter_id": encounter_id}

def eliminar(encounter_id: int) -> dict:
    df = _extraer()
    nuevo_df = df[df["encounter_id"] != encounter_id]
    if len(nuevo_df) == len(df):
        return {"error": "Registro no encontrado"}
    _cargar(nuevo_df)
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
    vistos_encounter: set[int] = set()

    for chunk in _iter_chunks():
        if chunk.empty:
            continue

        if "encounter_id" in chunk.columns:
            chunk = chunk.dropna(subset=["encounter_id"]).copy()
            chunk["encounter_id"] = chunk["encounter_id"].astype(int)
            chunk = chunk[~chunk["encounter_id"].isin(vistos_encounter)]
            if chunk.empty:
                continue
            vistos_encounter.update(chunk["encounter_id"].tolist())

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
    return {"total": len(df), "registros": _traducir_df(df.head(100)).fillna("").to_dict(orient="records")}