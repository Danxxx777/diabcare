"""Transformación en el almacén (paso T del ELT) — normaliza crudo ya cargado."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

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


def _normalizar_genero(v) -> str:
    try:
        from paquetes.dataset.DatasetTraducciones import normalizar_genero
        return normalizar_genero(v)
    except Exception:
        s = str(v or "").strip().lower()
        if s in ("m", "male", "masculino", "hombre"):
            return "Male"
        if s in ("f", "female", "femenino", "mujer"):
            return "Female"
        return "Other"


def _normalizar_tabaco(v) -> str:
    try:
        from paquetes.dataset.DatasetTraducciones import normalizar_tabaco
        return normalizar_tabaco(v)
    except Exception:
        return str(v or "No Info")


def transformar_registros(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
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
        work["gender"] = work["gender"].apply(_normalizar_genero)
    if "smoking_history" in work.columns:
        work["smoking_history"] = work["smoking_history"].apply(_normalizar_tabaco)

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
