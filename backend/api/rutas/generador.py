"""
generador.py — Genera registros sintéticos y los guarda como Parquet en stage/ y sube a MinIO
"""
import json
import random
import os
import pandas as pd
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from minio import Minio

enrutador = APIRouter()

STAGE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "stage"))
MINIO_HOST  = "localhost:9000"
MINIO_USER  = "admin"
MINIO_PASS  = "password123"
MINIO_BUCKET = "diabetes-data"

GENEROS     = ["Male", "Female", "Other"]
UBICACIONES = ["Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"]
HISTORIALES = ["never", "former", "current", "not current", "ever", "No Info"]


def _generar_registro(anio: int) -> dict:
    raza_aa = random.randint(0, 1)
    raza_as = random.randint(0, 1)
    raza_ca = random.randint(0, 1)
    raza_hi = random.randint(0, 1)
    raza_ot = 1 if not any([raza_aa, raza_as, raza_ca, raza_hi]) else random.randint(0, 1)
    hipertension = random.choices([0, 1], weights=[75, 25])[0]
    cardiopatia  = random.choices([0, 1], weights=[90, 10])[0]
    bmi          = round(random.uniform(15.0, 60.0), 2)
    hba1c        = round(random.uniform(3.5, 9.0), 1)
    glucosa      = random.randint(80, 300)
    prob = 0.05
    if hipertension: prob += 0.10
    if cardiopatia:  prob += 0.08
    if bmi > 30:     prob += 0.10
    if hba1c > 6.5:  prob += 0.30
    if glucosa > 140: prob += 0.20
    diabetes = 1 if random.random() < min(prob, 0.95) else 0
    return {
        "year": anio, "gender": random.choice(GENEROS),
        "age": round(random.uniform(0.08, 80.0), 2),
        "location": random.choice(UBICACIONES),
        "race_AfricanAmerican": raza_aa, "race_Asian": raza_as,
        "race_Caucasian": raza_ca, "race_Hispanic": raza_hi, "race_Other": raza_ot,
        "hypertension": hipertension, "heart_disease": cardiopatia,
        "smoking_history": random.choice(HISTORIALES),
        "bmi": bmi, "hbA1c_level": hba1c,
        "blood_glucose_level": glucosa, "diabetes": diabetes,
    }


def _stream_generacion(cantidad: int, anio: int):
    try:
        yield json.dumps({"progreso": 5, "mensaje": "Generando registros en memoria..."}) + "\n"
        registros = [_generar_registro(anio) for _ in range(cantidad)]
        yield json.dumps({"progreso": 55, "mensaje": f"{cantidad:,} registros generados"}) + "\n"

        df = pd.DataFrame(registros)
        yield json.dumps({"progreso": 70, "mensaje": "Convirtiendo a Parquet..."}) + "\n"

        os.makedirs(STAGE_DIR, exist_ok=True)
        nombre = f"sinteticos_{anio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        ruta   = os.path.join(STAGE_DIR, nombre)
        df.to_parquet(ruta, index=False)
        yield json.dumps({"progreso": 80, "mensaje": "Parquet guardado en stage/"}) + "\n"

        cliente = Minio(MINIO_HOST, access_key=MINIO_USER, secret_key=MINIO_PASS, secure=False)
        cliente.fput_object(MINIO_BUCKET, f"stage/{nombre}", ruta)
        yield json.dumps({"progreso": 98, "mensaje": f"Subido a MinIO: stage/{nombre}"}) + "\n"

        yield json.dumps({
            "progreso": 100,
            "listo": True,
            "mensaje": f"✅ {cantidad:,} registros guardados y subidos a MinIO como stage/{nombre}"
        }) + "\n"

    except Exception as e:
        yield json.dumps({"error": str(e)}) + "\n"


@enrutador.post("/api/generar-sinteticos")
def generar_sinteticos(payload: dict):
    cantidad = int(payload.get("cantidad", 100000))
    anio     = int(payload.get("anio", 2024))
    cantidad = max(1000, min(cantidad, 500000))
    return StreamingResponse(_stream_generacion(cantidad, anio), media_type="application/x-ndjson")