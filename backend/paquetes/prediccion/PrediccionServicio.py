import io
import pickle
import pandas as pd
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP   = "diabcare-app"
MODELO_PATH  = "modelos/modelo_diabetes.pkl"
HECHOS_PRED  = "hechos/hechos_prediccion.parquet"
FEATURES     = ["age", "bmi", "hbA1c_level", "blood_glucose_level", "hypertension", "heart_disease"]

_modelo_cache = {"modelo": None, "metricas": None}


def _sklearn():
    """Import diferido: sklearn/scipy son lentos al arrancar (sobre todo en Python 3.14)."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    return RandomForestClassifier, train_test_split, accuracy_score, precision_score, recall_score, f1_score


def _registrar_hecho_prediccion(datos: dict, resultado: dict, id_medico: str | None = None) -> None:
    """Persiste inferencia en hechos_prediccion."""
    try:
        import uuid
        from datetime import datetime, timezone
        c = get_cliente()
        cols = ["id_prediccion", "encounter_id", "probabilidad", "diagnostico_estimado",
                "modelo_version", "fecha_prediccion", "id_medico"]
        try:
            obj = c.get_object(BUCKET_APP, HECHOS_PRED)
            df = pd.read_parquet(io.BytesIO(obj.read()))
        except Exception:
            df = pd.DataFrame(columns=cols)
        fila = {
            "id_prediccion": str(uuid.uuid4()),
            "encounter_id": datos.get("encounter_id", ""),
            "probabilidad": resultado.get("probabilidad"),
            "diagnostico_estimado": resultado.get("resultado"),
            "modelo_version": "rf-v1",
            "fecha_prediccion": datetime.now(timezone.utc).isoformat(),
            "id_medico": id_medico or "",
        }
        _subir = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
        buf = io.BytesIO()
        _subir.to_parquet(buf, index=False)
        buf.seek(0)
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        c.put_object(BUCKET_APP, HECHOS_PRED, buf, buf.getbuffer().nbytes)
    except Exception:
        pass


def _cargar_modelo():
    if _modelo_cache["modelo"] is not None:
        return _modelo_cache["modelo"]
    try:
        c = get_cliente()
        obj = c.get_object(BUCKET_APP, MODELO_PATH)
        data = pickle.loads(obj.read())
        _modelo_cache["modelo"]   = data["modelo"]
        _modelo_cache["metricas"] = data["metricas"]
        return _modelo_cache["modelo"]
    except Exception:
        return None


def entrenar() -> dict:
    try:
        RandomForestClassifier, train_test_split, accuracy_score, precision_score, recall_score, f1_score = _sklearn()
        from paquetes.registros_clinicos.RegistrosClinicosServicio import _extraer
        df = _extraer()
        if df.empty:
            return {"error": "Dataset vacío"}

        df = df.dropna(subset=FEATURES + ["diabetes"])
        X = df[FEATURES].astype(float)
        y = df["diabetes"].astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Profundidad acotada: sin limite, sobre millones de filas el bosque
        # crece hasta gigabytes y tarda mas en cargarse que en predecir.
        modelo = RandomForestClassifier(
            n_estimators=60,
            max_depth=14,
            min_samples_leaf=25,
            random_state=42,
            n_jobs=-1,
        )
        modelo.fit(X_train, y_train)

        y_pred = modelo.predict(X_test)
        metricas = {
            "accuracy":  round(float(accuracy_score(y_test, y_pred)),  4),
            "precision": round(float(precision_score(y_test, y_pred)), 4),
            "recall":    round(float(recall_score(y_test, y_pred)),    4),
            "f1":        round(float(f1_score(y_test, y_pred)),        4),
            "registros_entrenamiento": len(X_train),
            "registros_prueba":        len(X_test),
        }

        # Guardar en MinIO
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        crudo = pickle.dumps({"modelo": modelo, "metricas": metricas})
        metricas["tamano_modelo_mb"] = round(len(crudo) / (1024 * 1024), 1)
        crudo = pickle.dumps({"modelo": modelo, "metricas": metricas})
        buf = io.BytesIO(crudo)
        buf.seek(0)
        c.put_object(BUCKET_APP, MODELO_PATH, buf, buf.getbuffer().nbytes)

        _modelo_cache["modelo"]   = modelo
        _modelo_cache["metricas"] = metricas

        return {"mensaje": "Modelo entrenado y guardado", **metricas}
    except Exception as e:
        return {"error": str(e)}


def predecir(datos: dict, id_medico: str | None = None) -> dict:
    modelo = _cargar_modelo()
    if modelo is None:
        return {"error": "Modelo no entrenado. Llama primero a POST /api/prediccion/entrenar"}
    try:
        X = pd.DataFrame([{f: float(datos.get(f, 0)) for f in FEATURES}])
        pred        = int(modelo.predict(X)[0])
        probabilidad = round(float(modelo.predict_proba(X)[0][1]), 4)

        # Interpretación clínica de factores de riesgo (complementa la caja negra del ML)
        factores = []
        age = float(datos.get("age", 0))
        bmi = float(datos.get("bmi", 0))
        hba = float(datos.get("hbA1c_level", 0))
        glc = float(datos.get("blood_glucose_level", 0))
        if hba >= 6.5:
            factores.append({"factor": "HbA1c", "valor": hba, "umbral": "≥ 6.5%", "nivel": "alto"})
        elif hba >= 5.7:
            factores.append({"factor": "HbA1c", "valor": hba, "umbral": "≥ 5.7%", "nivel": "medio"})
        if glc >= 126:
            factores.append({"factor": "Glucosa", "valor": glc, "umbral": "≥ 126 mg/dL", "nivel": "alto"})
        elif glc >= 100:
            factores.append({"factor": "Glucosa", "valor": glc, "umbral": "≥ 100 mg/dL", "nivel": "medio"})
        if bmi >= 30:
            factores.append({"factor": "BMI", "valor": bmi, "umbral": "≥ 30", "nivel": "alto"})
        elif bmi >= 25:
            factores.append({"factor": "BMI", "valor": bmi, "umbral": "≥ 25", "nivel": "medio"})
        if age >= 45:
            factores.append({"factor": "Edad", "valor": age, "umbral": "≥ 45 años", "nivel": "medio"})
        if int(datos.get("hypertension", 0)):
            factores.append({"factor": "Hipertensión", "valor": "Sí", "umbral": "presente", "nivel": "alto"})
        if int(datos.get("heart_disease", 0)):
            factores.append({"factor": "Cardiopatía", "valor": "Sí", "umbral": "presente", "nivel": "alto"})

        out = {
            "diagnostico":   pred,
            "resultado":     "Con diabetes" if pred == 1 else "Sin diabetes",
            "probabilidad":  probabilidad,
            "riesgo":        "Alto" if probabilidad >= 0.7 else "Medio" if probabilidad >= 0.4 else "Bajo",
            "factores_riesgo": factores,
        }
        _registrar_hecho_prediccion(datos, out, id_medico)
        return out
    except Exception as e:
        return {"error": str(e)}


def obtener_metricas() -> dict:
    _cargar_modelo()
    if _modelo_cache["metricas"] is None:
        return {"error": "Modelo no entrenado"}
    return _modelo_cache["metricas"]


def modelo_disponible() -> bool:
    """Si hay modelo entrenado, sin traerlo a memoria.

    Antes esto deserializaba el pickle completo; con un artefacto grande, abrir
    la pantalla de Prediccion se quedaba colgado casi un minuto.
    """
    if _modelo_cache["modelo"] is not None:
        return True
    try:
        get_cliente().stat_object(BUCKET_APP, MODELO_PATH)
        return True
    except Exception:
        return False
