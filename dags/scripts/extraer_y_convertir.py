"""
extraer_y_convertir.py
Extrae el dataset de PocketBase y lo guarda como archivo Parquet en la carpeta stage/.
"""

import json
import csv
import os
import urllib.request
from datetime import datetime
import pandas as pd

# ── Configuración ──────────────────────────────────────────────────────────────
PB_URL     = "http://host.docker.internal:8090"
PB_EMAIL   = "bloorm2@uteq.edu.ec"
PB_PASS    = "BDLM2106eslm2006.2018"
COLECCION  = "diabetes_dataset"
STAGE_DIR  = "/opt/airflow/stage"   
PAGE_SIZE  = 5000   # registros por página (máximo que acepta PocketBase)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _peticion(url: str, datos: dict = None, token: str = None) -> dict:
    """Realiza una petición HTTP a PocketBase y retorna el JSON."""
    cuerpo  = json.dumps(datos).encode() if datos else None
    metodo  = "POST" if datos else "GET"
    cabeceras = {"Content-Type": "application/json"}
    if token:
        cabeceras["Authorization"] = token
    req = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method=metodo)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def autenticar() -> str:
    """Obtiene el token de superusuario de PocketBase."""
    print("🔑 Autenticando en PocketBase...")
    resp  = _peticion(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        {"identity": PB_EMAIL, "password": PB_PASS},
    )
    token = resp["token"]
    print("   Token obtenido correctamente.")
    return token


def extraer_registros(token: str) -> list[dict]:
    """Extrae todos los registros de la colección paginando."""
    print(f"📥 Extrayendo registros de '{COLECCION}'...")
    registros = []
    pagina    = 1

    while True:
        url  = f"{PB_URL}/api/collections/{COLECCION}/records?page={pagina}&perPage={PAGE_SIZE}"
        resp = _peticion(url, token=token)
        items = resp.get("items", [])
        registros.extend(items)
        total_paginas = resp.get("totalPages", 1)
        print(f"   Página {pagina}/{total_paginas} — {len(registros)} registros acumulados")

        if pagina >= total_paginas:
            break
        pagina += 1

    print(f"   Total extraídos: {len(registros)}")
    return registros


def convertir_a_dataframe(registros: list[dict]) -> pd.DataFrame:
    """Convierte la lista de registros en un DataFrame limpio."""
    print("🔄 Convirtiendo a DataFrame...")

    # Columnas que queremos conservar (ignoramos id, collectionId, etc.)
    columnas = [
        "year", "gender", "age", "location",
        "race_AfricanAmerican", "race_Asian", "race_Caucasian",
        "race_Hispanic", "race_Other",
        "hypertension", "heart_disease", "smoking_history",
        "bmi", "hbA1c_level", "blood_glucose_level", "diabetes",
    ]

    filas = []
    for r in registros:
        fila = {col: r.get(col) for col in columnas}
        filas.append(fila)

    df = pd.DataFrame(filas)

    # Tipado explícito
    df["year"]                 = pd.to_numeric(df["year"],                 errors="coerce").astype("Int32")
    df["age"]                  = pd.to_numeric(df["age"],                  errors="coerce").astype(float)
    df["race_AfricanAmerican"] = pd.to_numeric(df["race_AfricanAmerican"], errors="coerce").astype("Int8")
    df["race_Asian"]           = pd.to_numeric(df["race_Asian"],           errors="coerce").astype("Int8")
    df["race_Caucasian"]       = pd.to_numeric(df["race_Caucasian"],       errors="coerce").astype("Int8")
    df["race_Hispanic"]        = pd.to_numeric(df["race_Hispanic"],        errors="coerce").astype("Int8")
    df["race_Other"]           = pd.to_numeric(df["race_Other"],           errors="coerce").astype("Int8")
    df["hypertension"]         = pd.to_numeric(df["hypertension"],         errors="coerce").astype("Int8")
    df["heart_disease"]        = pd.to_numeric(df["heart_disease"],        errors="coerce").astype("Int8")
    df["bmi"]                  = pd.to_numeric(df["bmi"],                  errors="coerce").astype(float)
    df["hbA1c_level"]          = pd.to_numeric(df["hbA1c_level"],          errors="coerce").astype(float)
    df["blood_glucose_level"]  = pd.to_numeric(df["blood_glucose_level"],  errors="coerce").astype("Int32")
    df["diabetes"]             = pd.to_numeric(df["diabetes"],             errors="coerce").astype("Int8")

    print(f"   DataFrame listo: {df.shape[0]} filas × {df.shape[1]} columnas")
    return df


def guardar_parquet(df: pd.DataFrame) -> str:
    """Guarda el DataFrame como Parquet en stage/ y retorna la ruta."""
    os.makedirs(STAGE_DIR, exist_ok=True)
    nombre    = f"diabetes_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
    ruta      = os.path.join(STAGE_DIR, nombre)
    df.to_parquet(ruta, index=False, engine="pyarrow")
    tam_mb    = os.path.getsize(ruta) / 1_048_576
    print(f"💾 Parquet guardado en: {ruta}  ({tam_mb:.2f} MB)")
    return ruta


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  DiabCare — Extracción y Conversión a Parquet")
    print("=" * 60)

    token     = autenticar()
    registros = extraer_registros(token)
    df        = convertir_a_dataframe(registros)
    ruta      = guardar_parquet(df)

    print()
    print("✅ Proceso completado.")
    print(f"   Archivo listo en: {ruta}")
    return ruta


if __name__ == "__main__":
    main()
