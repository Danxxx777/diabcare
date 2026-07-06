from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.prediccion.PrediccionServicio import entrenar, predecir, obtener_metricas, modelo_disponible

router = APIRouter(prefix="/api/prediccion", tags=["Predicción"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


def _auditar(usuario: str, tipo: str, detalle: str):
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, tipo, "prediccion", detalle)
    except Exception:
        pass


class DatosPrediccion(BaseModel):
    age: float
    bmi: float
    hbA1c_level: float
    blood_glucose_level: float
    hypertension: int = 0
    heart_disease: int = 0


@router.post("/entrenar")
def entrenar_modelo(payload: dict = Depends(require_modulo("prediccion"))):
    res = entrenar()
    if "error" not in res:
        _auditar(_usuario(payload), "update",
                 f"Modelo reentrenado accuracy={res.get('accuracy')}")
    return res


@router.post("/")
def predecir_diabetes(datos: DatosPrediccion, payload: dict = Depends(require_modulo("prediccion"))):
    medico_id = payload.get("sub") or payload.get("id") or ""
    res = predecir(datos.dict(), id_medico=str(medico_id) if payload.get("rol") == "medico" else None)
    if "error" not in res:
        _auditar(_usuario(payload), "read",
                 f"Predicción: {res.get('resultado')} (p={res.get('probabilidad')})")
    return res


@router.get("/metricas")
def metricas(payload: dict = Depends(require_modulo("prediccion"))):
    return obtener_metricas()


@router.get("/estado")
def estado(payload: dict = Depends(require_modulo("prediccion"))):
    disponible = modelo_disponible()
    return {
        "modelo_disponible": disponible,
        "mensaje": "Modelo listo para predicciones" if disponible else
        "Modelo no entrenado. Usa POST /api/prediccion/entrenar",
    }
