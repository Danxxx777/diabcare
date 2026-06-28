import io
import pandas as pd
from datetime import datetime
from servicios.configuracion.ConfiguracionClienteMinio import get_cliente
from servicios.configuracion.ConfiguracionAjustes import MINIO_BUCKET, MINIO_STAGE_PATH

ARCHIVO_PRINCIPAL = f"{MINIO_STAGE_PATH}diabetes_dataset_20260519_182447.parquet"
_cache = {"df": None}

def _extraer() -> pd.DataFrame:
    try:
        c = get_cliente()
        objetos = list(c.list_objects(MINIO_BUCKET, prefix=MINIO_STAGE_PATH))
        dfs = []
        for obj in objetos:
            if obj.object_name.endswith('.parquet'):
                data = c.get_object(MINIO_BUCKET, obj.object_name)
                dfs.append(pd.read_parquet(io.BytesIO(data.read())))
        if not dfs:
            return pd.DataFrame()
        df = pd.concat(dfs, ignore_index=True)
        if 'encounter_id' not in df.columns:
            df.insert(0, 'encounter_id', range(1, len(df) + 1))
        _cache["df"] = df.copy()
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
    except Exception as e:
        print(f"[ELT] Error cargando: {e}")

def listar(limit: int = 50, offset: int = 0, filtros: dict = None) -> dict:
    df = _extraer()
    if filtros:
        if filtros.get("diabetes") is not None:
            df = df[df["diabetes"] == filtros["diabetes"]]
        if filtros.get("gender"):
            df = df[df["gender"] == filtros["gender"]]
        if filtros.get("location"):
            df = df[df["location"].str.contains(str(filtros["location"]), case=False, na=False)]
        if filtros.get("age_min") is not None:
            df = df[df["age"] >= filtros["age_min"]]
        if filtros.get("age_max") is not None:
            df = df[df["age"] <= filtros["age_max"]]
    total = len(df)
    chunk = df.iloc[offset:offset + limit]
    return {"total": total, "registros": chunk.fillna("").to_dict(orient="records")}

def obtener(encounter_id: int) -> dict:
    df = _extraer()
    fila = df[df["encounter_id"] == encounter_id]
    if fila.empty:
        return {"error": "Registro no encontrado"}
    return fila.fillna("").iloc[0].to_dict()

def crear(datos: dict) -> dict:
    df = _extraer()
    nuevo_id = int(df["encounter_id"].max()) + 1 if not df.empty else 1
    datos["encounter_id"] = nuevo_id
    datos["created_at"] = datetime.utcnow().isoformat()
    nuevo_df = pd.concat([df, pd.DataFrame([datos])], ignore_index=True)
    _cargar(nuevo_df)
    return {"mensaje": "Registro creado", "encounter_id": nuevo_id}

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

def estadisticas() -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0}

    con = df[df["diabetes"] == 1]
    sin = df[df["diabetes"] == 0]

    genero_counts = df["gender"].value_counts().to_dict()

    tabaquismo = {}
    for val in df["smoking_history"].dropna().unique():
        sub = df[df["smoking_history"] == val]
        tabaquismo[val] = {
            "con_diabetes": int((sub["diabetes"] == 1).sum()),
            "sin_diabetes": int((sub["diabetes"] == 0).sum()),
        }

    razas = ["race_AfricanAmerican", "race_Asian", "race_Caucasian", "race_Hispanic", "race_Other"]
    raza_counts = {}
    for r in razas:
        if r in df.columns:
            raza_counts[r] = {
                "con_diabetes": int(df[df["diabetes"] == 1][r].sum()),
                "sin_diabetes": int(df[df["diabetes"] == 0][r].sum()),
            }

    bins   = [0, 20, 30, 40, 50, 60, 70, 200]
    labels = ["<20", "20-30", "31-40", "41-50", "51-60", "61-70", "70+"]
    df["rango_edad"] = pd.cut(df["age"], bins=bins, labels=labels, right=True)
    edad_group = df.groupby(["rango_edad", "diabetes"], observed=True).size().unstack(fill_value=0)
    edad_data = {}
    for lbl in labels:
        if lbl in edad_group.index:
            edad_data[lbl] = {
                "sin_diabetes": int(edad_group.loc[lbl].get(0, 0)),
                "con_diabetes": int(edad_group.loc[lbl].get(1, 0)),
            }
        else:
            edad_data[lbl] = {"sin_diabetes": 0, "con_diabetes": 0}

    promedios = {
        "bmi":    {"con": round(float(con["bmi"].mean()), 2) if not con.empty else 0,
                   "sin": round(float(sin["bmi"].mean()), 2) if not sin.empty else 0},
        "hba1c":  {"con": round(float(con["hbA1c_level"].mean()), 2) if not con.empty else 0,
                   "sin": round(float(sin["hbA1c_level"].mean()), 2) if not sin.empty else 0},
        "glucosa":{"con": round(float(con["blood_glucose_level"].mean()), 1) if not con.empty else 0,
                   "sin": round(float(sin["blood_glucose_level"].mean()), 1) if not sin.empty else 0},
    }

    comorbilidades = {
        "hipertension": {
            "con_diabetes_con": int(df[(df["diabetes"]==1) & (df["hypertension"]==1)].shape[0]),
            "con_diabetes_sin": int(df[(df["diabetes"]==1) & (df["hypertension"]==0)].shape[0]),
            "sin_diabetes_con": int(df[(df["diabetes"]==0) & (df["hypertension"]==1)].shape[0]),
            "sin_diabetes_sin": int(df[(df["diabetes"]==0) & (df["hypertension"]==0)].shape[0]),
        },
        "cardiopatia": {
            "con_diabetes_con": int(df[(df["diabetes"]==1) & (df["heart_disease"]==1)].shape[0]),
            "con_diabetes_sin": int(df[(df["diabetes"]==1) & (df["heart_disease"]==0)].shape[0]),
            "sin_diabetes_con": int(df[(df["diabetes"]==0) & (df["heart_disease"]==1)].shape[0]),
            "sin_diabetes_sin": int(df[(df["diabetes"]==0) & (df["heart_disease"]==0)].shape[0]),
        },
    }

    top_ubicaciones = df["location"].value_counts().head(10).to_dict()

    tendencia_data = []
    if "year" in df.columns:
        tendencia = df.groupby("year")["diabetes"].agg(
            total="count",
            con_diabetes=lambda x: (x == 1).sum()
        ).reset_index()
        tendencia_data = [
            {"year": int(row["year"]), "total": int(row["total"]), "con_diabetes": int(row["con_diabetes"])}
            for _, row in tendencia.iterrows()
        ]

    return {
        "total":          len(df),
        "con_diabetes":   int((df["diabetes"] == 1).sum()),
        "sin_diabetes":   int((df["diabetes"] == 0).sum()),
        "genero":         genero_counts,
        "tabaquismo":     tabaquismo,
        "razas":          raza_counts,
        "edad":           edad_data,
        "promedios":      promedios,
        "comorbilidades": comorbilidades,
        "ubicaciones":    top_ubicaciones,
        "tendencia":      tendencia_data,
    }

def buscar(filtros: dict) -> dict:
    df = _extraer()
    if filtros.get("diabetes") is not None:
        df = df[df["diabetes"] == filtros["diabetes"]]
    if filtros.get("gender"):
        df = df[df["gender"] == filtros["gender"]]
    if filtros.get("location"):
        df = df[df["location"].str.contains(filtros["location"], case=False, na=False)]
    if filtros.get("age_min"):
        df = df[df["age"] >= filtros["age_min"]]
    if filtros.get("age_max"):
        df = df[df["age"] <= filtros["age_max"]]
    return {"total": len(df), "registros": df.head(100).fillna("").to_dict(orient="records")}