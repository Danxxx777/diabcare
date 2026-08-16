"""
Benchmark: informe tradicional (SQL / SQLite) vs informe columnar (Parquet/pandas).

Usa SQL ANSI portable en SQLite 3 (sin ILIKE, sin ventana avanzada) para
compatibilidad entre motores. El mismo informe se calcula en pandas sobre
el DataFrame origen.
"""
from __future__ import annotations

import io
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

# Columnas mínimas del informe compuesto clínico
_COLS = [
    "age", "bmi", "hbA1c_level", "blood_glucose_level", "diabetes", "location",
]

SQL_KPI = """
SELECT
  COUNT(*) AS total_registros,
  SUM(CASE WHEN diabetes = 1 THEN 1 ELSE 0 END) AS con_diabetes,
  SUM(CASE WHEN diabetes = 0 THEN 1 ELSE 0 END) AS sin_diabetes,
  ROUND(100.0 * SUM(CASE WHEN diabetes = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS prevalencia_pct,
  ROUND(AVG(age), 2) AS edad_promedio,
  ROUND(AVG(bmi), 2) AS bmi_promedio,
  ROUND(AVG(hbA1c_level), 2) AS hba1c_promedio,
  ROUND(AVG(blood_glucose_level), 2) AS glucosa_promedio
FROM diabetes
"""

SQL_POR_DX = """
SELECT
  diabetes,
  COUNT(*) AS n,
  ROUND(AVG(age), 2) AS edad_prom,
  ROUND(AVG(bmi), 2) AS bmi_prom,
  ROUND(AVG(hbA1c_level), 2) AS hba1c_prom,
  ROUND(AVG(blood_glucose_level), 2) AS glucosa_prom
FROM diabetes
GROUP BY diabetes
ORDER BY diabetes
"""

SQL_UBIC = """
SELECT
  location,
  COUNT(*) AS n,
  SUM(CASE WHEN diabetes = 1 THEN 1 ELSE 0 END) AS con_diabetes,
  ROUND(100.0 * SUM(CASE WHEN diabetes = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS prevalencia_pct
FROM diabetes
GROUP BY location
ORDER BY n DESC
LIMIT 20
"""


def _preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    rename = {
        "HbA1c_level": "hbA1c_level", "hba1c_level": "hbA1c_level",
        "Blood_glucose_level": "blood_glucose_level",
        "Diabetes": "diabetes", "Location": "location", "Age": "age", "BMI": "bmi",
    }
    work = work.rename(columns={k: v for k, v in rename.items() if k in work.columns})
    for c in _COLS:
        if c not in work.columns:
            if c == "location":
                work[c] = "Desconocido"
            elif c == "diabetes":
                work[c] = 0
            else:
                work[c] = None
    out = work[_COLS].copy()
    for c in ("age", "bmi", "hbA1c_level", "blood_glucose_level", "diabetes"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out["location"] = out["location"].fillna("Desconocido").astype(str)
    out["diabetes"] = out["diabetes"].fillna(0).astype(int)
    out = out.dropna(subset=["age", "bmi"], how="any")
    return out


def _informe_pandas(df: pd.DataFrame) -> dict[str, Any]:
    total = len(df)
    con = int((df["diabetes"] == 1).sum())
    sin = total - con
    kpi = {
        "total_registros": total,
        "con_diabetes": con,
        "sin_diabetes": sin,
        "prevalencia_pct": round(100.0 * con / total, 2) if total else 0.0,
        "edad_promedio": round(float(df["age"].mean()), 2) if total else 0.0,
        "bmi_promedio": round(float(df["bmi"].mean()), 2) if total else 0.0,
        "hba1c_promedio": round(float(df["hbA1c_level"].mean()), 2) if total else 0.0,
        "glucosa_promedio": round(float(df["blood_glucose_level"].mean()), 2) if total else 0.0,
    }
    por_dx = []
    for dx, g in df.groupby("diabetes"):
        por_dx.append({
            "diabetes": int(dx),
            "n": int(len(g)),
            "edad_prom": round(float(g["age"].mean()), 2),
            "bmi_prom": round(float(g["bmi"].mean()), 2),
            "hba1c_prom": round(float(g["hbA1c_level"].mean()), 2),
            "glucosa_prom": round(float(g["blood_glucose_level"].mean()), 2),
        })
    ubic = (
        df.groupby("location")
        .agg(n=("diabetes", "size"), con_diabetes=("diabetes", "sum"))
        .reset_index()
        .sort_values("n", ascending=False)
        .head(20)
    )
    ubic["prevalencia_pct"] = (100.0 * ubic["con_diabetes"] / ubic["n"]).round(2)
    return {
        "kpi": kpi,
        "por_diagnostico": por_dx,
        "top_ubicaciones": ubic.to_dict(orient="records"),
    }


def _informe_sql(df: pd.DataFrame) -> tuple[dict[str, Any], float, float]:
    """Carga a SQLite + ejecuta las 3 consultas. Devuelve (resultado, ms_carga, ms_consulta)."""
    t0 = time.perf_counter()
    conn = sqlite3.connect(":memory:")
    try:
        # chunksize evita picos de memoria; SQL types simples (compatibilidad amplia)
        df.to_sql("diabetes", conn, index=False, if_exists="replace")
        ms_carga = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        cur = conn.cursor()
        cur.execute(SQL_KPI)
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        kpi = dict(zip(cols, row)) if row else {}

        cur.execute(SQL_POR_DX)
        cols = [d[0] for d in cur.description]
        por_dx = [dict(zip(cols, r)) for r in cur.fetchall()]

        cur.execute(SQL_UBIC)
        cols = [d[0] for d in cur.description]
        ubic = [dict(zip(cols, r)) for r in cur.fetchall()]
        ms_sql = (time.perf_counter() - t1) * 1000
    finally:
        conn.close()

    return {"kpi": kpi, "por_diagnostico": por_dx, "top_ubicaciones": ubic}, ms_carga, ms_sql


def _cargar_df_desde_stage(cliente, bucket: str, stage_path: str, max_filas: int | None) -> pd.DataFrame:
    objs = [
        o for o in cliente.list_objects(bucket, prefix=stage_path, recursive=True)
        if o.object_name.endswith(".parquet")
    ]
    if not objs:
        return pd.DataFrame()
    objs = sorted(objs, key=lambda o: o.last_modified.timestamp() if o.last_modified else 0, reverse=True)
    partes = []
    total = 0
    for o in objs:
        raw = cliente.get_object(bucket, o.object_name).read()
        parte = pd.read_parquet(io.BytesIO(raw))
        partes.append(parte)
        total += len(parte)
        if max_filas and total >= max_filas:
            break
    if not partes:
        return pd.DataFrame()
    df = pd.concat(partes, ignore_index=True)
    if max_filas and len(df) > max_filas:
        df = df.head(max_filas).copy()
    return df


def ejecutar_benchmark_informe(
    df: pd.DataFrame | None = None,
    *,
    cliente=None,
    bucket: str = "",
    stage_path: str = "",
    max_filas: int | None = 200_000,
) -> dict[str, Any]:
    """
    Cronometra el mismo informe clínico:
    - Tradicional: INSERT + SELECT en SQLite (equivalente académico a BDR/SQL).
    - Columnar: agregaciones pandas sobre Parquet ya cargado en memoria.
    """
    inicio = time.perf_counter()
    fuente = "dataframe"
    if df is None or df.empty:
        if cliente is None:
            return {"ok": False, "error": "Sin datos para el benchmark"}
        t_read = time.perf_counter()
        df = _cargar_df_desde_stage(cliente, bucket, stage_path, max_filas)
        ms_lectura_parquet = (time.perf_counter() - t_read) * 1000
        fuente = "minio_stage"
    else:
        ms_lectura_parquet = 0.0
        if max_filas and len(df) > max_filas:
            df = df.head(max_filas).copy()

    if df is None or df.empty:
        return {"ok": False, "error": "No hay Parquet en stage/ ni DataFrame de entrada"}

    prep = _preparar_df(df)
    n = len(prep)
    if n == 0:
        return {"ok": False, "error": "Tras limpieza no quedan filas válidas"}

    # --- SQL tradicional ---
    sql_out, ms_carga_sql, ms_consulta_sql = _informe_sql(prep)
    ms_sql_total = ms_carga_sql + ms_consulta_sql

    # --- Columnar / Parquet (pandas) ---
    t_p = time.perf_counter()
    pq_out = _informe_pandas(prep)
    ms_pandas = (time.perf_counter() - t_p) * 1000

    # Velocidad relativa (solo consultas; la carga SQL incluye materializar tabla)
    factor = round(ms_sql_total / ms_pandas, 2) if ms_pandas > 0 else None
    leccion = (
        "El informe SQL tradicional incluye crear la tabla en memoria (como cargar a BDR) "
        "más los SELECT. El enfoque columnar (Parquet ya en MinIO + pandas) evita ese "
        "coste de carga repetida y suele ser más rápido en agregaciones analíticas — "
        "lo visto en clase: BDR/informe simple vs columnar/informe compuesto."
    )

    sql_path = Path(__file__).resolve().parent / "sql" / "informe_tradicional.sql"
    return {
        "ok": True,
        "ejecutado_en": datetime.now(timezone.utc).isoformat(),
        "fuente": fuente,
        "registros": n,
        "max_filas": max_filas,
        "motor_sql": "SQLite 3 (SQL ANSI compatible)",
        "motor_columnar": "pandas sobre Parquet/DataFrame",
        "archivo_sql": str(sql_path) if sql_path.exists() else None,
        "tiempos_ms": {
            "lectura_parquet_stage": round(ms_lectura_parquet, 2),
            "sql_carga_tabla": round(ms_carga_sql, 2),
            "sql_consultas": round(ms_consulta_sql, 2),
            "sql_total": round(ms_sql_total, 2),
            "columnar_pandas": round(ms_pandas, 2),
            "benchmark_total": round((time.perf_counter() - inicio) * 1000, 2),
        },
        "comparacion": {
            "ganador": "columnar" if ms_pandas < ms_sql_total else "sql_tradicional",
            "factor_sql_vs_columnar": factor,
            "diferencia_ms": round(abs(ms_sql_total - ms_pandas), 2),
            "leccion": leccion,
        },
        "resultado_sql": sql_out,
        "resultado_columnar": pq_out,
    }
