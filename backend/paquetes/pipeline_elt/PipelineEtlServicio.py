"""
PipelineEtlServicio — P8 Pipeline ELT (Extract → Load → Transform).

Sincroniza incrementally registros clínicos desde PocketBase hacia MinIO.
La generación masiva de datos sintéticos es responsabilidad del Generador (P4).
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente, verificar_conexion
from paquetes.configuracion.ConfiguracionAjustes import (
    MINIO_BUCKET,
    MINIO_STAGE_PATH,
    POCKETBASE_URL,
    POCKETBASE_EMAIL,
    POCKETBASE_PASSWORD,
    POCKETBASE_COLLECTION,
)
from paquetes.dataset.DatasetTraducciones import normalizar_genero, normalizar_tabaco

BUCKET_APP = "diabcare-app"
SYNC_STATE_KEY = "pipeline/sync_state.json"
PB_PAGE_SIZE = 500
PREFIJO_PIPELINE = "pocketbase_elt_"
PREFIJO_GENERADOR = "sinteticos_"


def _origen_archivo(nombre: str) -> str:
    base = nombre.split("/")[-1]
    if base.startswith(PREFIJO_PIPELINE):
        return "elt"
    if PREFIJO_GENERADOR in base or base.startswith("sinteticos"):
        return "generador"
    return "otro"

RAZAS = [
    "race_AfricanAmerican", "race_Asian", "race_Caucasian",
    "race_Hispanic", "race_Other",
]
COLUMNAS_STAGE = [
    "year", "gender", "age", "location", "hypertension", "heart_disease",
    "smoking_history", "bmi", "hbA1c_level", "blood_glucose_level", "diabetes",
] + RAZAS

_RENAME = {
    "Gender": "gender", "gender": "gender",
    "Age": "age", "age": "age",
    "Hypertension": "hypertension", "hypertension": "hypertension",
    "Heart_disease": "heart_disease", "heart_disease": "heart_disease",
    "Smoking_history": "smoking_history", "smoking_history": "smoking_history",
    "BMI": "bmi", "bmi": "bmi",
    "HbA1c_level": "hbA1c_level", "hba1c_level": "hbA1c_level", "HbA1c": "hbA1c_level",
    "Blood_glucose_level": "blood_glucose_level", "blood_glucose_level": "blood_glucose_level",
    "Diabetes": "diabetes", "diabetes": "diabetes",
    "Location": "location", "location": "location",
    "Year": "year", "year": "year",
}


def _http_json(url: str, method: str = "GET", data: dict | None = None, token: str | None = None, timeout: float = 60):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = token
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalle = ""
        try:
            detalle = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise RuntimeError(f"Error HTTP PocketBase ({e.code}): {e.reason}. {detalle[:200]}") from e


def _probar_http(url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def _conectividad() -> dict:
    return {
        "minio": "conectado" if verificar_conexion() else "sin conexión",
        "pocketbase": "conectado" if _probar_http(f"{POCKETBASE_URL}/api/health") else "sin conexión",
        "airflow": "conectado" if _probar_http("http://localhost:8080/health") else "sin conexión",
    }


def _leer_sync_state() -> dict:
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            return {}
        obj = c.get_object(BUCKET_APP, SYNC_STATE_KEY)
        return json.loads(obj.read().decode("utf-8"))
    except Exception:
        return {}


def _guardar_sync_state(state: dict) -> None:
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    contenido = json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")
    c.put_object(BUCKET_APP, SYNC_STATE_KEY, io.BytesIO(contenido), length=len(contenido),
                 content_type="application/json")


def _parse_pb_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        s = str(val).replace("Z", "+00:00")
        if " " in s and "T" not in s:
            s = s.replace(" ", "T", 1)
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _fmt_pb_filter(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


def obtener_estado() -> dict:
    try:
        c = get_cliente()
        objetos = list(c.list_objects(MINIO_BUCKET, prefix=MINIO_STAGE_PATH, recursive=True))
        parquets = [o for o in objetos if o.object_name.endswith(".parquet")]
        parquets_sorted = sorted(
            parquets,
            key=lambda o: o.last_modified.timestamp() if o.last_modified else 0,
            reverse=True,
        )
        archivos_elt = [o for o in parquets if _origen_archivo(o.object_name) == "elt"]
        archivos_gen = [o for o in parquets if _origen_archivo(o.object_name) == "generador"]

        archivos = []
        for obj in parquets_sorted[:15]:
            nombre_corto = obj.object_name.replace(MINIO_STAGE_PATH, "")
            archivos.append({
                "nombre": nombre_corto,
                "ruta": obj.object_name,
                "tamano_mb": round(obj.size / 1024 / 1024, 2),
                "fecha": obj.last_modified.strftime("%Y-%m-%d %H:%M:%S") if obj.last_modified else "—",
                "origen": _origen_archivo(obj.object_name),
            })

        ultimo = parquets_sorted[0] if parquets_sorted else None
        sync = _leer_sync_state()
        conn = _conectividad()

        total_registros = 0
        try:
            from paquetes.registros_clinicos import RegistrosClinicosServicio
            total_registros = int(RegistrosClinicosServicio.estadisticas().get("total") or 0)
        except Exception:
            pass

        return {
            "estado": "activo" if conn["minio"] == "conectado" else "degradado",
            "bucket": MINIO_BUCKET,
            "prefix": MINIO_STAGE_PATH,
            "total_archivos": len(parquets),
            "total_elt": len(archivos_elt),
            "total_generador": len(archivos_gen),
            "total_stage": len(parquets),
            "total_registros": total_registros,
            "ultimo_archivo": ultimo.object_name.replace(MINIO_STAGE_PATH, "") if ultimo else None,
            "ultima_fecha": ultimo.last_modified.strftime("%Y-%m-%d %H:%M:%S") if ultimo and ultimo.last_modified else None,
            "archivos": archivos,
            "conectividad": conn,
            "sincronizacion": {
                "ultima": sync.get("ultima_sincronizacion"),
                "registros_acumulados": sync.get("registros_acumulados", 0),
                "inicializado": bool(sync.get("inicializado")),
            },
        }
    except Exception as e:
        return {"estado": "error", "detalle": str(e), "conectividad": _conectividad()}


def _autenticar_pocketbase() -> str | None:
    credenciales = {"identity": POCKETBASE_EMAIL, "password": POCKETBASE_PASSWORD}
    for ruta in ("/api/collections/_superusers/auth-with-password", "/api/admins/auth-with-password"):
        try:
            res = _http_json(f"{POCKETBASE_URL}{ruta}", "POST", credenciales, timeout=15)
            if res.get("token"):
                return res["token"]
        except Exception:
            continue
    return None


def _filtro_incremental(desde: datetime) -> str:
    """Sintaxis PocketBase: comillas dobles en literales de fecha."""
    return f'updated>"{_fmt_pb_filter(desde)}"'


def _paginar_pocketbase(token: str | None, filtro_pb: str | None) -> list[pd.DataFrame]:
    partes: list[pd.DataFrame] = []
    pagina = 1
    while True:
        url = (
            f"{POCKETBASE_URL}/api/collections/{POCKETBASE_COLLECTION}/records"
            f"?page={pagina}&perPage={PB_PAGE_SIZE}"
        )
        if filtro_pb:
            url += f"&filter={urllib.parse.quote(filtro_pb, safe='')}"
        try:
            data = _http_json(url, token=token, timeout=120)
        except urllib.error.URLError as e:
            raise RuntimeError(f"PocketBase no disponible en {POCKETBASE_URL}.") from e
        except RuntimeError as e:
            msg = str(e)
            if "401" in msg or "403" in msg:
                if token is None:
                    raise RuntimeError(
                        "PocketBase requiere autenticación. Revise POCKETBASE_EMAIL/PASSWORD."
                    ) from e
            if "404" in msg:
                raise RuntimeError(f"Colección '{POCKETBASE_COLLECTION}' no encontrada.") from e
            raise

        items = data.get("items") or []
        if not items:
            break
        partes.append(pd.DataFrame(items))
        if pagina >= int(data.get("totalPages") or 1):
            break
        pagina += 1
    return partes


def _filtrar_cliente(df: pd.DataFrame, desde: datetime) -> pd.DataFrame:
    if df.empty or "updated" not in df.columns:
        return df.iloc[0:0]
    upd = df["updated"].apply(_parse_pb_dt)
    return df[upd > desde].copy()


def _extraer_pocketbase(token: str | None, desde: datetime | None, historico: bool) -> tuple[pd.DataFrame, str]:
    filtro_pb = None if historico else (_filtro_incremental(desde) if desde else None)
    filtro_local = False

    try:
        partes = _paginar_pocketbase(token, filtro_pb)
    except RuntimeError as e:
        if filtro_pb and "400" in str(e) and not historico:
            partes = _paginar_pocketbase(token, None)
            filtro_local = True
        else:
            raise

    if not partes:
        if historico:
            return pd.DataFrame(), "0 registros en PocketBase (colección vacía)"
        return pd.DataFrame(), "0 registros nuevos en PocketBase desde la última sincronización"

    df = pd.concat(partes, ignore_index=True)
    if not historico and desde and filtro_local:
        df = _filtrar_cliente(df, desde)

    if df.empty:
        return pd.DataFrame(), "0 registros nuevos en PocketBase desde la última sincronización"

    if historico:
        det = f"{len(df):,} registros extraídos (importación histórica)".replace(",", ".")
    elif filtro_local:
        det = f"{len(df):,} registros nuevos/actualizados (filtro local)".replace(",", ".")
    else:
        det = f"{len(df):,} registros nuevos/actualizados en PocketBase".replace(",", ".")
    return df, det


def _transformar(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    if df.empty:
        raise RuntimeError("No hay datos para transformar")

    work = df.copy()
    meta = {"id", "created", "updated", "collectionId", "collectionName", "expand"}
    work = work.drop(columns=[c for c in work.columns if c in meta], errors="ignore")
    work = work.rename(columns={k: v for k, v in _RENAME.items() if k in work.columns})

    for col in RAZAS:
        if col not in work.columns:
            work[col] = 0
    if "year" not in work.columns:
        work["year"] = datetime.now(timezone.utc).year
    if "location" not in work.columns:
        work["location"] = "Desconocido"
    if "smoking_history" not in work.columns:
        work["smoking_history"] = "Sin información"

    if "gender" in work.columns:
        work["gender"] = work["gender"].apply(normalizar_genero)
    if "smoking_history" in work.columns:
        work["smoking_history"] = work["smoking_history"].apply(normalizar_tabaco)

    for col in ("hypertension", "heart_disease"):
        if col not in work.columns:
            work[col] = 0
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0).astype(int)

    if "diabetes" not in work.columns:
        hba = pd.to_numeric(work["hbA1c_level"], errors="coerce") if "hbA1c_level" in work.columns else 0
        glc = pd.to_numeric(work["blood_glucose_level"], errors="coerce") if "blood_glucose_level" in work.columns else 0
        work["diabetes"] = ((hba > 6.5) | (glc > 200)).fillna(0).astype(int)
    else:
        work["diabetes"] = pd.to_numeric(work["diabetes"], errors="coerce").fillna(0).astype(int)

    for col in ("age", "bmi", "hbA1c_level", "blood_glucose_level", "year"):
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    for col in RAZAS:
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0).astype(int)

    work = work.dropna(subset=["age", "bmi"], how="any")
    faltantes = [c for c in COLUMNAS_STAGE if c not in work.columns]
    if faltantes:
        raise RuntimeError(f"Columnas clínicas faltantes: {', '.join(faltantes)}")

    out = work[COLUMNAS_STAGE].copy()
    out["location"] = out["location"].fillna("Desconocido").astype(str)
    out["smoking_history"] = out["smoking_history"].fillna("Sin información").astype(str)

    eliminados = len(df) - len(out)
    det = f"{len(out):,} registros normalizados".replace(",", ".")
    if eliminados:
        det += f" ({eliminados} descartados por nulos)"
    return out, det


def _cargar_minio(df: pd.DataFrame) -> tuple[str, str]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    nombre = f"{PREFIJO_PIPELINE}{ts}.parquet"
    ruta = f"{MINIO_STAGE_PATH}{nombre}"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name
        df.to_parquet(tmp_path, index=False, engine="pyarrow")
        c = get_cliente()
        if not c.bucket_exists(MINIO_BUCKET):
            c.make_bucket(MINIO_BUCKET)
        with open(tmp_path, "rb") as f:
            data = f.read()
        c.put_object(MINIO_BUCKET, ruta, io.BytesIO(data), length=len(data),
                     content_type="application/octet-stream")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    mb = round(len(data) / 1024 / 1024, 2)
    return nombre, f"Delta cargado ({mb} MB) — {nombre}"


def _estado_almacen() -> str:
    """Resumen del DWH en MinIO (incluye archivos del Generador)."""
    try:
        from paquetes.registros_clinicos import RegistrosClinicosServicio
        stats = RegistrosClinicosServicio.estadisticas()
        total = int(stats.get("total") or 0)
        c = get_cliente()
        objs = [
            o for o in c.list_objects(MINIO_BUCKET, prefix=MINIO_STAGE_PATH, recursive=True)
            if o.object_name.endswith(".parquet")
        ]
        sint = sum(1 for o in objs if "sinteticos_" in o.object_name.split("/")[-1])
        if sint:
            return (
                f"MinIO OK — {total:,} registros en stage/ "
                f"({sint} archivo(s) del Generador). Ya disponibles en Dashboard."
            ).replace(",", ".")
        return f"MinIO OK — {total:,} registros en stage/".replace(",", ".")
    except Exception:
        return "Los datos del Generador ya están en MinIO; revise Dashboard o Estadísticas."


def _mensaje_sin_pocketbase() -> str:
    return (
        "MinIO actualizado. Si usó el Generador, los datos ya están en stage/. "
        "Este botón solo trae novedades desde PocketBase."
    )


def _verificar_consumo(nuevos: int) -> str:
    try:
        from paquetes.registros_clinicos import RegistrosClinicosServicio
        RegistrosClinicosServicio.invalidar_cache()
        return f"Caché actualizada — {nuevos:,} registros sincronizados en esta ejecución".replace(",", ".")
    except Exception as e:
        return f"Parquet cargado ({e})"


def _inicializar_sync() -> dict:
    ahora = datetime.now(timezone.utc)
    _guardar_sync_state({
        "ultima_sincronizacion": ahora.isoformat(),
        "inicializado": True,
        "registros_acumulados": 0,
    })
    return {
        "ok": True,
        "mensaje": (
            "Sincronización inicializada. El pipeline solo traerá registros nuevos de PocketBase. "
            "Para datos sintéticos masivos use Dataset → Generador."
        ),
        "registros": 0,
        "pasos": [
            {"paso": 1, "nombre": "Extracción PocketBase", "estado": "ok",
             "detalle": "Marca de tiempo inicial creada — sin importación masiva"},
            {"paso": 2, "nombre": "Transformación pandas", "estado": "ok", "detalle": "Omitido (0 registros nuevos)"},
            {"paso": 3, "nombre": "Carga MinIO (Parquet)", "estado": "ok", "detalle": "Omitido (0 registros nuevos)"},
            {"paso": 4, "nombre": "Consumo FastAPI", "estado": "ok", "detalle": "Listo para próximas sincronizaciones"},
        ],
        "conectividad": _conectividad(),
    }


def _paso_materializar_dwh() -> dict:
    try:
        from paquetes.dataset.DatasetDwhServicio import materializar_dwh
        dwh = materializar_dwh()
        if dwh.get("ok"):
            det = (
                f"DWH materializado — {dwh.get('hechos', 0):,} hechos, "
                f"{dwh.get('dim_paciente', 0)} pac., {dwh.get('dim_ubicacion', 0)} ubic., "
                f"{dwh.get('dim_tiempo', 0)} periodos"
            ).replace(",", ".")
            return {"paso": 0, "nombre": "Transformación Hecho-Dim", "estado": "ok", "detalle": det}
        return {"paso": 0, "nombre": "Transformación Hecho-Dim", "estado": "error",
                "detalle": dwh.get("error", "Sin datos en stage/")}
    except Exception as e:
        return {"paso": 0, "nombre": "Transformación Hecho-Dim", "estado": "error", "detalle": str(e)}


def ejecutar_elt(usuario: str = "sistema", historico: bool = False) -> dict:
    inicio = time.perf_counter()
    pasos: list[dict] = []
    conn = _conectividad()

    if conn["minio"] != "conectado":
        return {"ok": False, "error": "MinIO no disponible.", "pasos": pasos, "conectividad": conn}
    if conn["pocketbase"] != "conectado":
        return {"ok": False, "error": f"PocketBase no disponible en {POCKETBASE_URL}.",
                "pasos": pasos, "conectividad": conn}

    sync = _leer_sync_state()
    if not sync.get("inicializado") and not historico:
        return _inicializar_sync()

    desde = _parse_pb_dt(sync.get("ultima_sincronizacion"))

    try:
        token = _autenticar_pocketbase()
        crudo, det_ext = _extraer_pocketbase(token, desde, historico)

        if crudo.empty:
            almacen = _estado_almacen()
            pasos.append({"paso": 1, "nombre": "Extracción PocketBase", "estado": "ok", "detalle": det_ext})
            pasos.append({"paso": 2, "nombre": "Carga MinIO (Parquet)", "estado": "ok",
                          "detalle": "Omitido — sin datos nuevos en PocketBase"})
            dwh_paso = _paso_materializar_dwh()
            dwh_paso["paso"] = 3
            pasos.append(dwh_paso)
            pasos.append({"paso": 4, "nombre": "Consumo FastAPI", "estado": "ok", "detalle": almacen})
            return {
                "ok": True,
                "mensaje": _mensaje_sin_pocketbase(),
                "registros": 0,
                "pasos": pasos,
                "conectividad": conn,
                "informativo": True,
            }

        pasos.append({"paso": 1, "nombre": "Extracción PocketBase", "estado": "ok", "detalle": det_ext})
        limpio, det_trans = _transformar(crudo)
        pasos.append({"paso": 2, "nombre": "Transformación pandas", "estado": "ok", "detalle": det_trans})

        archivo, det_carga = _cargar_minio(limpio)
        pasos.append({"paso": 3, "nombre": "Carga MinIO (Parquet)", "estado": "ok", "detalle": det_carga})

        dwh_paso = _paso_materializar_dwh()
        dwh_paso["paso"] = 4
        pasos.append(dwh_paso)

        det_api = _verificar_consumo(len(limpio))
        pasos.append({"paso": 5, "nombre": "Consumo FastAPI", "estado": "ok", "detalle": det_api})

        ahora = datetime.now(timezone.utc)
        if "updated" in crudo.columns:
            max_upd = crudo["updated"].apply(_parse_pb_dt).dropna()
            if not max_upd.empty:
                ahora = max(max_upd)

        acum = int(sync.get("registros_acumulados") or 0) + len(limpio)
        _guardar_sync_state({
            "ultima_sincronizacion": ahora.isoformat(),
            "inicializado": True,
            "registros_acumulados": acum,
        })

    except Exception as e:
        paso = len(pasos) + 1
        pasos.append({"paso": paso, "nombre": "Pipeline ELT", "estado": "error", "detalle": str(e)})
        return {"ok": False, "error": str(e), "pasos": pasos, "conectividad": conn}

    duracion = round(time.perf_counter() - inicio, 1)
    registros = len(limpio)

    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "execute", "pipeline_elt", f"Sync incremental — {registros} reg. → {archivo}")
    except Exception:
        pass

    return {
        "ok": True,
        "mensaje": f"Sincronizados {registros:,} registros desde PocketBase".replace(",", "."),
        "archivo": archivo,
        "registros": registros,
        "duracion_seg": duracion,
        "pasos": pasos,
        "conectividad": conn,
    }
