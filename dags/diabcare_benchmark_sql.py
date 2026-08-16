"""DAG benchmark: informe SQL tradicional (SQLite) vs Parquet/pandas."""
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
DAG_ID = "diabcare_benchmark_sql"


def _post_json(path: str, body: dict, timeout: float = 900) -> dict:
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


def benchmark(**_):
    result = _post_json("/api/pipeline/benchmark-sql-interno", {"max_filas": 200000})
    if result.get("ok") is False:
        raise RuntimeError(result.get("error") or "Benchmark falló")
    return {
        "registros": result.get("registros"),
        "tiempos_ms": result.get("tiempos_ms"),
        "comparacion": result.get("comparacion"),
    }


with DAG(
    dag_id=DAG_ID,
    description="Compara informe SQL tradicional vs columnar Parquet (tiempos)",
    default_args={"owner": "diabcare", "retries": 0},
    start_date=datetime(2026, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["diabcare", "benchmark", "sql", "parquet"],
    max_active_runs=1,
) as dag:
    PythonOperator(task_id="verificar_api", python_callable=verificar_api) >> \
        PythonOperator(task_id="benchmark_sql_vs_parquet", python_callable=benchmark)
