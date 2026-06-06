from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from servicios.prediccion.PrediccionServicio import entrenar, predecir, obtener_metricas, modelo_disponible

router = APIRouter(prefix="/api/prediccion", tags=["Predicción"])


class DatosPrediccion(BaseModel):
    age:                float
    bmi:                float
    hbA1c_level:        float
    blood_glucose_level: float
    hypertension:       int = 0
    heart_disease:      int = 0


@router.post("/entrenar")
def entrenar_modelo():
    return entrenar()


@router.post("/")
def predecir_diabetes(datos: DatosPrediccion):
    return predecir(datos.dict())


@router.get("/metricas")
def metricas():
    return obtener_metricas()


@router.get("/estado")
def estado():
    disponible = modelo_disponible()
    return {
        "modelo_disponible": disponible,
        "mensaje": "Modelo listo para predicciones" if disponible else "Modelo no entrenado. Usa POST /api/prediccion/entrenar"
    }
