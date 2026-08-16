"""DAG DiabCare ELT histórico — relee PocketBase completo (domingos 03:00)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

DIABCARE_API = os.environ.get("DIABCARE_API", "http://host.docker.internal:8000").rstrip("/")
PIPELINE_KEY = os.environ.get("DIABCARE_PIPELINE_KEY", "diabcare-pipeline-demo")
DAG_ID = "diabcare_elt_historico"


def _post_json(path: str, body: dict, timeout: float = 1800) -> dict:
    url = f"{DIABCARE_API}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
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
        raise RuntimeError(f"HTTP {e.code}: {detalle}") from e


def verificar_api(**_):
    url = f"{DIABCARE_API}/api/pipeline/estado-publico"
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(str(payload))
    return payload


def ejecutar_historico(**context):
    result = _post_json("/api/pipeline/ejecutar-interno", {"historico": True})
    if result.get("ok") is False:
        raise RuntimeError(result.get("error") or "ELT histórico falló")
    return {
        "registros": result.get("registros"),
        "duracion_seg": result.get("duracion_seg"),
        "tiempos": result.get("tiempos"),
        "archivo": result.get("archivo"),
    }


with DAG(
    dag_id=DAG_ID,
    description="DiabCare ELT histórico completo (no borra stage; añade Parquet + rematerializa DWH)",
    default_args={
        "owner": "diabcare",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 3 * * 0",
    catchup=False,
    tags=["diabcare", "elt", "historico"],
    max_active_runs=1,
) as dag:
    PythonOperator(task_id="verificar_api", python_callable=verificar_api) >> \
        PythonOperator(task_id="elt_historico_completo", python_callable=ejecutar_historico)
