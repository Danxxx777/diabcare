"""
Pasos E·L·T del pipeline (orden ELT real: Extraer → Cargar → Transformar).

Work area: diabcare-app/pipeline/work/{run_id}/raw.parquet
Landing (L): diabetes-data/landing/  — datos crudos en el almacén
Stage (T):   diabetes-data/stage/    — datos normalizados para consumo/DWH

Estrategia: incremental (no borra landing/stage); histórico solo relee PocketBase.
"""
from __future__ import annotations

import io
import json
import secrets
import time
from datetime import datetime, timezone

import pandas as pd

from etl.extract import autenticar_pocketbase, extraer_desde_pocketbase, parse_pb_dt
from etl.transform import transformar_registros
from etl.load import cargar_parquet_minio, PREFIJO_RAW, PREFIJO_PIPELINE
from etl.benchmark_sql import ejecutar_benchmark_informe

from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
from paquetes.configuracion.ConfiguracionAjustes import (
    MINIO_BUCKET,
    MINIO_STAGE_PATH,
    POCKETBASE_URL,
    POCKETBASE_EMAIL,
    POCKETBASE_PASSWORD,
    POCKETBASE_COLLECTION,
)

BUCKET_APP = "diabcare-app"
SYNC_STATE_KEY = "pipeline/sync_state.json"
WORK_PREFIX = "pipeline/work/"
BENCHMARK_KEY = "pipeline/benchmark_ultimo.json"
LAST_RUN_KEY = "pipeline/ultima_corrida.json"
# Landing fuera de stage/ para no contaminar lecturas clínicas (RegistrosClinicos).
LANDING_PATH = "landing/"


def nuevo_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{ts}_{secrets.token_hex(3)}"


def _leer_json(key: str) -> dict:
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            return {}
        obj = c.get_object(BUCKET_APP, key)
        return json.loads(obj.read().decode("utf-8"))
    except Exception:
        return {}


def _guardar_json(key: str, data: dict) -> None:
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    contenido = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    c.put_object(
        BUCKET_APP, key, io.BytesIO(contenido), length=len(contenido),
        content_type="application/json",
    )


def leer_sync_state() -> dict:
    return _leer_json(SYNC_STATE_KEY)


def guardar_sync_state(state: dict) -> None:
    _guardar_json(SYNC_STATE_KEY, state)


def leer_ultima_corrida() -> dict:
    return _leer_json(LAST_RUN_KEY)


def leer_benchmark_ultimo() -> dict:
    return _leer_json(BENCHMARK_KEY)


def _subir_df_work(run_id: str, nombre: str, df: pd.DataFrame) -> str:
    key = f"{WORK_PREFIX}{run_id}/{nombre}"
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    data = buf.getvalue()
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    c.put_object(BUCKET_APP, key, io.BytesIO(data), length=len(data),
                 content_type="application/octet-stream")
    return key


def _leer_df_work(run_id: str, nombre: str) -> pd.DataFrame:
    key = f"{WORK_PREFIX}{run_id}/{nombre}"
    c = get_cliente()
    obj = c.get_object(BUCKET_APP, key)
    return pd.read_parquet(io.BytesIO(obj.read()))


def paso_extraer(*, historico: bool = False, run_id: str | None = None) -> dict:
    """E — Extraer desde PocketBase (aún no toca el almacén analítico)."""
    inicio = time.perf_counter()
    run_id = run_id or nuevo_run_id()
    sync = leer_sync_state()

    if not sync.get("inicializado") and not historico:
        ahora = datetime.now(timezone.utc)
        guardar_sync_state({
            "ultima_sincronizacion": ahora.isoformat(),
            "inicializado": True,
            "registros_acumulados": 0,
        })
        dur = round(time.perf_counter() - inicio, 3)
        return {
            "ok": True,
            "paso": "extraer",
            "run_id": run_id,
            "registros": 0,
            "omitir_siguientes": True,
            "detalle": "Sincronización inicializada — sin importación masiva",
            "duracion_seg": dur,
            "inicializado": True,
        }

    token = autenticar_pocketbase(POCKETBASE_URL, POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
    desde = parse_pb_dt(sync.get("ultima_sincronizacion"))
    df, detalle = extraer_desde_pocketbase(
        base_url=POCKETBASE_URL,
        coleccion=POCKETBASE_COLLECTION,
        token=token,
        desde=desde,
        historico=historico,
    )
    if not df.empty:
        _subir_df_work(run_id, "raw.parquet", df)
        meta = {"historico": historico, "filas": len(df)}
        if "updated" in df.columns:
            max_upd = df["updated"].apply(parse_pb_dt).dropna()
            if not max_upd.empty:
                meta["max_updated"] = max(max_upd).isoformat()
        _guardar_json(f"{WORK_PREFIX}{run_id}/meta.json", meta)

    dur = round(time.perf_counter() - inicio, 3)
    return {
        "ok": True,
        "paso": "extraer",
        "run_id": run_id,
        "registros": int(len(df)),
        "omitir_siguientes": bool(df.empty),
        "detalle": detalle,
        "duracion_seg": dur,
        "work": f"{WORK_PREFIX}{run_id}/raw.parquet" if not df.empty else None,
    }


def paso_cargar(*, run_id: str) -> dict:
    """
    L — Cargar datos CRUDOS al almacén (MinIO landing/).
    En ELT la transformación ocurre después, ya dentro del storage.
    """
    inicio = time.perf_counter()
    if not run_id:
        return {"ok": False, "paso": "cargar", "error": "run_id requerido"}
    try:
        raw = _leer_df_work(run_id, "raw.parquet")
    except Exception as e:
        return {"ok": False, "paso": "cargar", "run_id": run_id,
                "error": f"No hay raw.parquet para run_id={run_id}: {e}"}

    c = get_cliente()
    archivo, det_carga = cargar_parquet_minio(
        raw,
        cliente=c,
        bucket=MINIO_BUCKET,
        stage_path=LANDING_PATH,
        prefijo=PREFIJO_RAW,
        etiqueta="Landing crudo cargado",
    )
    meta = _leer_json(f"{WORK_PREFIX}{run_id}/meta.json")
    meta["landing"] = f"{LANDING_PATH}{archivo}"
    meta["landing_archivo"] = archivo
    _guardar_json(f"{WORK_PREFIX}{run_id}/meta.json", meta)

    dur = round(time.perf_counter() - inicio, 3)
    return {
        "ok": True,
        "paso": "cargar",
        "run_id": run_id,
        "registros": int(len(raw)),
        "archivo": archivo,
        "ruta": f"{LANDING_PATH}{archivo}",
        "detalle": det_carga,
        "duracion_seg": dur,
    }


def paso_transformar(*, run_id: str, materializar: bool = True) -> dict:
    """
    T — Transformar en el almacén: normaliza crudo → stage/ + DWH Hecho-Dim.
    """
    inicio = time.perf_counter()
    if not run_id:
        return {"ok": False, "paso": "transformar", "error": "run_id requerido"}

    meta = _leer_json(f"{WORK_PREFIX}{run_id}/meta.json")
    try:
        raw = _leer_df_work(run_id, "raw.parquet")
    except Exception:
        landing = meta.get("landing")
        if not landing:
            return {"ok": False, "paso": "transformar", "run_id": run_id,
                    "error": f"No hay raw ni landing para run_id={run_id}"}
        try:
            c = get_cliente()
            obj = c.get_object(MINIO_BUCKET, landing)
            raw = pd.read_parquet(io.BytesIO(obj.read()))
        except Exception as e:
            return {"ok": False, "paso": "transformar", "run_id": run_id,
                    "error": f"No se pudo leer landing: {e}"}

    limpio, detalle = transformar_registros(raw)
    _subir_df_work(run_id, "clean.parquet", limpio)

    c = get_cliente()
    archivo, det_stage = cargar_parquet_minio(
        limpio,
        cliente=c,
        bucket=MINIO_BUCKET,
        stage_path=MINIO_STAGE_PATH,
        prefijo=PREFIJO_PIPELINE,
        etiqueta="Stage limpio (post-T)",
    )

    dwh_detalle = None
    if materializar:
        try:
            from paquetes.dataset.DatasetDwhServicio import materializar_dwh
            dwh = materializar_dwh()
            if dwh.get("ok"):
                dwh_detalle = (
                    f"DWH — {dwh.get('hechos', 0):,} hechos".replace(",", ".")
                )
            else:
                dwh_detalle = dwh.get("error", "DWH sin datos")
        except Exception as e:
            dwh_detalle = str(e)

    try:
        from paquetes.registros_clinicos import RegistrosClinicosServicio
        RegistrosClinicosServicio.invalidar_cache()
    except Exception:
        pass

    sync = leer_sync_state()
    ahora = datetime.now(timezone.utc)
    if meta.get("max_updated"):
        try:
            ahora = parse_pb_dt(meta["max_updated"]) or ahora
        except Exception:
            pass
    acum = int(sync.get("registros_acumulados") or 0) + len(limpio)
    guardar_sync_state({
        "ultima_sincronizacion": ahora.isoformat(),
        "inicializado": True,
        "registros_acumulados": acum,
    })

    dur = round(time.perf_counter() - inicio, 3)
    return {
        "ok": True,
        "paso": "transformar",
        "run_id": run_id,
        "registros": int(len(limpio)),
        "archivo": archivo,
        "detalle": f"{detalle} · {det_stage}",
        "dwh": dwh_detalle,
        "duracion_seg": dur,
        "work": f"{WORK_PREFIX}{run_id}/clean.parquet",
    }


def ejecutar_pasos_completos(
    usuario: str = "sistema",
    *,
    historico: bool = False,
    run_id: str | None = None,
) -> dict:
    """Orquesta E→L→T (ELT real)."""
    inicio = time.perf_counter()
    pasos: list[dict] = []
    run_id = run_id or nuevo_run_id()

    ext = paso_extraer(historico=historico, run_id=run_id)
    pasos.append({
        "paso": 1, "nombre": "Extracción PocketBase (E)",
        "estado": "ok" if ext.get("ok") else "error",
        "detalle": ext.get("detalle") or ext.get("error", ""),
        "duracion_seg": ext.get("duracion_seg"),
    })
    if not ext.get("ok"):
        return _fallo(pasos, ext.get("error"), inicio, run_id)

    if ext.get("omitir_siguientes") or ext.get("registros", 0) == 0:
        dwh_paso = _materializar_solo()
        dwh_paso["paso"] = 3
        pasos.append({
            "paso": 2, "nombre": "Carga MinIO landing (L)", "estado": "ok",
            "detalle": "Omitido — sin datos nuevos en PocketBase",
        })
        pasos.append(dwh_paso)
        pasos.append({
            "paso": 4, "nombre": "Consumo FastAPI", "estado": "ok",
            "detalle": "Caché lista; use Generador para cargas masivas sintéticas",
        })
        out = {
            "ok": True,
            "mensaje": (
                "MinIO actualizado. Si usó el Generador, los datos ya están en stage/. "
                "Este botón solo trae novedades desde PocketBase."
            ),
            "registros": 0,
            "run_id": run_id,
            "pasos": pasos,
            "duracion_seg": round(time.perf_counter() - inicio, 1),
            "tiempos": _tiempos_desde_pasos(pasos),
            "informativo": True,
            "patron": "ELT",
        }
        _guardar_corrida(out, usuario)
        return out

    ld = paso_cargar(run_id=run_id)
    pasos.append({
        "paso": 2, "nombre": "Carga MinIO landing (L)",
        "estado": "ok" if ld.get("ok") else "error",
        "detalle": ld.get("detalle") or ld.get("error", ""),
        "duracion_seg": ld.get("duracion_seg"),
    })
    if not ld.get("ok"):
        return _fallo(pasos, ld.get("error"), inicio, run_id)

    tr = paso_transformar(run_id=run_id, materializar=True)
    pasos.append({
        "paso": 3, "nombre": "Transformación stage + DWH (T)",
        "estado": "ok" if tr.get("ok") else "error",
        "detalle": tr.get("detalle") or tr.get("error", ""),
        "duracion_seg": tr.get("duracion_seg"),
    })
    if not tr.get("ok"):
        return _fallo(pasos, tr.get("error"), inicio, run_id)

    pasos.append({
        "paso": 4, "nombre": "Hecho-Dimensión (parte de T)",
        "estado": "ok",
        "detalle": tr.get("dwh") or "DWH materializado",
    })
    pasos.append({
        "paso": 5, "nombre": "Consumo FastAPI",
        "estado": "ok",
        "detalle": f"Caché actualizada — {tr.get('registros', 0)} registros",
    })

    dur = round(time.perf_counter() - inicio, 1)
    out = {
        "ok": True,
        "mensaje": f"ELT: {tr.get('registros', 0):,} registros (E→L→T)".replace(",", "."),
        "archivo": tr.get("archivo"),
        "landing": ld.get("ruta"),
        "registros": tr.get("registros", 0),
        "run_id": run_id,
        "duracion_seg": dur,
        "patron": "ELT",
        "tiempos": {
            "extraer_seg": ext.get("duracion_seg"),
            "cargar_seg": ld.get("duracion_seg"),
            "transformar_seg": tr.get("duracion_seg"),
            "total_seg": dur,
        },
        "pasos": pasos,
    }
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "execute", "pipeline_elt",
                  f"ELT run={run_id} — {out['registros']} reg. → {out.get('archivo')}")
    except Exception:
        pass
    _guardar_corrida(out, usuario)
    return out


def _materializar_solo() -> dict:
    try:
        from paquetes.dataset.DatasetDwhServicio import materializar_dwh
        dwh = materializar_dwh()
        if dwh.get("ok"):
            det = f"DWH materializado — {dwh.get('hechos', 0):,} hechos".replace(",", ".")
            return {"paso": 0, "nombre": "Transformación Hecho-Dim (T)", "estado": "ok", "detalle": det}
        return {"paso": 0, "nombre": "Transformación Hecho-Dim (T)", "estado": "error",
                "detalle": dwh.get("error", "Sin datos")}
    except Exception as e:
        return {"paso": 0, "nombre": "Transformación Hecho-Dim (T)", "estado": "error", "detalle": str(e)}


def _tiempos_desde_pasos(pasos: list[dict]) -> dict:
    return {
        "total_seg": sum(float(p.get("duracion_seg") or 0) for p in pasos),
        "por_paso": [
            {"nombre": p.get("nombre"), "duracion_seg": p.get("duracion_seg")}
            for p in pasos if p.get("duracion_seg") is not None
        ],
    }


def _fallo(pasos: list[dict], error: str | None, inicio: float, run_id: str) -> dict:
    out = {
        "ok": False,
        "error": error or "Error en pipeline",
        "run_id": run_id,
        "pasos": pasos,
        "duracion_seg": round(time.perf_counter() - inicio, 1),
        "patron": "ELT",
    }
    _guardar_corrida(out, "sistema")
    return out


def _guardar_corrida(out: dict, usuario: str) -> None:
    try:
        _guardar_json(LAST_RUN_KEY, {
            "ok": out.get("ok"),
            "usuario": usuario,
            "run_id": out.get("run_id"),
            "registros": out.get("registros"),
            "duracion_seg": out.get("duracion_seg"),
            "tiempos": out.get("tiempos"),
            "patron": out.get("patron", "ELT"),
            "mensaje": out.get("mensaje") or out.get("error"),
            "fin": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass


def correr_benchmark(max_filas: int | None = 200_000) -> dict:
    c = get_cliente()
    result = ejecutar_benchmark_informe(
        None,
        cliente=c,
        bucket=MINIO_BUCKET,
        stage_path=MINIO_STAGE_PATH,
        max_filas=max_filas,
    )
    if result.get("ok"):
        try:
            _guardar_json(BENCHMARK_KEY, result)
        except Exception:
            pass
    return result
