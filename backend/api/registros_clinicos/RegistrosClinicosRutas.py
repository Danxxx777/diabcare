from fastapi import APIRouter
router = APIRouter(prefix='/api/registros', tags=['Registros Clinicos'])
from fastapi import APIRouter, Header, Query
from pydantic import BaseModel
from typing import Optional
from servicios.registros_clinicos.RegistrosClinicosServicio import (
    listar, obtener, crear, actualizar, eliminar, buscar
)

router = APIRouter(prefix="/api/registros", tags=["Registros Clínicos"])

class RegistroEntrada(BaseModel):
    year: int
    gender: str
    age: float
    location: str
    hypertension: int = 0
    heart_disease: int = 0
    smoking_history: str = "never"
    bmi: float = 0.0
    hbA1c_level: float = 0.0
    blood_glucose_level: int = 0
    diabetes: int = 0

class ActualizarEntrada(BaseModel):
    bmi: Optional[float] = None
    hbA1c_level: Optional[float] = None
    blood_glucose_level: Optional[int] = None
    diabetes: Optional[int] = None
    hypertension: Optional[int] = None
    heart_disease: Optional[int] = None

@router.get("/")
def listar_registros(limit: int = Query(50, le=500), offset: int = Query(0)):
    return listar(limit, offset)

@router.get("/buscar")
def buscar_registros(
    diabetes: Optional[int] = None,
    gender: Optional[str] = None,
    location: Optional[str] = None,
    age_min: Optional[float] = None,
    age_max: Optional[float] = None
):
    return buscar({"diabetes": diabetes, "gender": gender, "location": location, "age_min": age_min, "age_max": age_max})

@router.get("/estadisticas")
def estadisticas():
    from servicios.registros_clinicos.RegistrosClinicosServicio import _extraer
    df = _extraer()
    if df.empty:
        return {"total": 0, "con_diabetes": 0, "sin_diabetes": 0}
    return {
        "total": len(df),
        "con_diabetes": int((df["diabetes"] == 1).sum()),
        "sin_diabetes": int((df["diabetes"] == 0).sum()),
    }
 
@router.get("/{encounter_id}")
def obtener_registro(encounter_id: int):
    return obtener(encounter_id)

@router.post("/")
def crear_registro(datos: RegistroEntrada):
    return crear(datos.dict())

@router.put("/{encounter_id}")
def actualizar_registro(encounter_id: int, datos: ActualizarEntrada):
    return actualizar(encounter_id, datos.dict(exclude_none=True))

@router.delete("/{encounter_id}")
def eliminar_registro(encounter_id: int):
    return eliminar(encounter_id)