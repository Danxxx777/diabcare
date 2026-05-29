import io
import uuid
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

def listar(limit: int = 50, offset: int = 0) -> dict:
    df = _extraer()
    total = len(df)
    chunk = df.iloc[offset:offset+limit]
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