import io
import uuid
import random
import pandas as pd
from datetime import datetime
from servicios.configuracion.ConfiguracionClienteMinio import get_cliente
from servicios.configuracion.ConfiguracionAjustes import MINIO_BUCKET, MINIO_STAGE_PATH

UBICACIONES = [
    "Alabama", "California", "Texas", "Florida", "Nueva York",
    "Georgia", "Ohio", "Michigan", "Arizona", "Nevada",
    "Colorado", "Washington", "Oregón", "Illinois", "Pensilvania"
]

RAZAS = {
    "race_AfricanAmerican": 0,
    "race_Asian": 0,
    "race_Caucasian": 0,
    "race_Hispanic": 0,
    "race_Other": 0
}

HISTORIAL_TABAQUISMO = ["nunca", "actual", "no actual", "Sin información"]

def generar_registro(year: int) -> dict:
    edad = round(random.uniform(1, 80), 1)
    bmi = round(random.uniform(15, 45), 2)
    hba1c = round(random.uniform(3.5, 9.0), 1)
    glucosa = random.randint(80, 300)
    diabetes = 1 if (hba1c > 6.5 or glucosa > 200) else (1 if random.random() < 0.15 else 0)
    hiper = 1 if (bmi > 30 and random.random() < 0.4) else (1 if random.random() < 0.1 else 0)
    cardio = 1 if (diabetes and random.random() < 0.3) else (1 if random.random() < 0.05 else 0)
    raza = {k: 0 for k in RAZAS}
    raza[random.choice(list(RAZAS.keys()))] = 1
    return {
        "year": year,
        "gender": random.choice(["Masculino", "Femenino", "Otro"]),
        "age": edad,
        "location": random.choice(UBICACIONES),
        **raza,
        "hypertension": hiper,
        "heart_disease": cardio,
        "smoking_history": random.choice(HISTORIAL_TABAQUISMO),
        "bmi": bmi,
        "hbA1c_level": hba1c,
        "blood_glucose_level": glucosa,
        "diabetes": diabetes
    }

def generar_y_subir(cantidad: int = 100000, year: int = 2025) -> dict:
    try:
        registros = [generar_registro(year) for _ in range(cantidad)]
        df = pd.DataFrame(registros)
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archivo = f"{MINIO_STAGE_PATH}sinteticos_{year}_{timestamp}.parquet"
        c = get_cliente()
        c.put_object(MINIO_BUCKET, archivo, buf, buf.getbuffer().nbytes)
        return {"mensaje": f"{cantidad} registros generados y subidos", "archivo": archivo, "total": cantidad}
    except Exception as e:
        return {"error": str(e)}