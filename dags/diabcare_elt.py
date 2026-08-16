"""
DAG DiabCare ELT incremental — orden real Extraer → Cargar → Transformar.

Schedule: cada hora. Disparable desde DiabCare o Airflow UI.
PocketBase → landing/ (L) → stage/ + DWH (T).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator

DIABCARE_API = os.environ.get("DIABCARE_API", "http://host.docker.internal:8000").rstrip("/")
PIPELINE_KEY = os.environ.get("DIABCARE_PIPELINE_KEY", "diabcare-pipeline-demo")
DAG_ID = "diabcare_elt"


def _post_json(path: str, body: dict, timeout: float = 600) -> dict:
    url = f"{DIABCARE_API}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-DiabCare-Pipeline-Key": PIPELINE_KEY,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"HTTP {e.code} al llamar {url}: {detalle}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"No se pudo conectar a DiabCare API ({url}). ¿uvicorn en :8000?"
        ) from e


def verificar_api(**_context):
    url = f"{DIABCARE_API}/api/pipeline/estado-publico"
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(f"API DiabCare no lista: {payload}")
    return payload


def extraer(**context):
    conf = (context.get("dag_run").conf if context.get("dag_run") else None) or {}
    historico = bool(conf.get("historico", False))
    result = _post_json("/api/pipeline/ejecutar-interno/extraer", {"historico": historico})
    if result.get("ok") is False:
        raise RuntimeError(result.get("error") or "Extracción falló")
    ti = context["ti"]
    ti.xcom_push(key="run_id", value=result.get("run_id"))
    ti.xcom_push(key="omitir", value=bool(result.get("omitir_siguientes") or result.get("registros") == 0))
    ti.xcom_push(key="extraer_seg", value=result.get("duracion_seg"))
    return result


def hay_datos(**context):
    omitir = context["ti"].xcom_pull(task_ids="extraer_pocketbase", key="omitir")
    return not bool(omitir)


def cargar(**context):
    """L — crudo a MinIO landing/."""
    run_id = context["ti"].xcom_pull(task_ids="extraer_pocketbase", key="run_id")
    result = _post_json("/api/pipeline/ejecutar-interno/cargar", {"run_id": run_id})
    if result.get("ok") is False:
        raise RuntimeError(result.get("error") or "Carga falló")
    context["ti"].xcom_push(key="cargar_seg", value=result.get("duracion_seg"))
    return result


def transformar(**context):
    """T — normaliza en almacén → stage/ + DWH."""
    run_id = context["ti"].xcom_pull(task_ids="extraer_pocketbase", key="run_id")
    result = _post_json("/api/pipeline/ejecutar-interno/transformar", {"run_id": run_id})
    if result.get("ok") is False:
        raise RuntimeError(result.get("error") or "Transformación falló")
    context["ti"].xcom_push(key="transformar_seg", value=result.get("duracion_seg"))
    return result


default_args = {
    "owner": "diabcare",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id=DAG_ID,
    description="DiabCare ELT: Extraer → Cargar (landing) → Transformar (stage+DWH)",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    tags=["diabcare", "elt", "incremental", "minio", "pocketbase"],
    max_active_runs=1,
) as dag:
    t_ping = PythonOperator(task_id="verificar_api_diabcare", python_callable=verificar_api)
    t_ext = PythonOperator(task_id="extraer_pocketbase", python_callable=extraer)
    t_gate = ShortCircuitOperator(task_id="hay_datos_nuevos", python_callable=hay_datos)
    t_ld = PythonOperator(task_id="cargar_landing_minio", python_callable=cargar)
    t_tr = PythonOperator(task_id="transformar_stage_dwh", python_callable=transformar)
    t_ping >> t_ext >> t_gate >> t_ld >> t_tr
