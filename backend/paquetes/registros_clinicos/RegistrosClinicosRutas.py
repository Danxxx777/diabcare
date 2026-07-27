from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from typing import Optional

from nucleo.utilidades.Dependencias import require_modulo, require_auth
from paquetes.registros_clinicos.RegistrosClinicosServicio import (
    listar, obtener, crear, actualizar, eliminar, buscar,
    estadisticas as _estadisticas,
    calidad_diabetes as _calidad_diabetes,
)

router = APIRouter(prefix="/api/registros", tags=["Registros Clínicos"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


def _auditar(usuario: str, tipo: str, detalle: str):
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, tipo, "registros", detalle)
    except Exception:
        pass


class RegistroEntrada(BaseModel):
    year: int
    gender: str
    age: int
    location: str
    hypertension: int = 0
    heart_disease: int = 0
    smoking_history: str = "never"
    bmi: float = 0.0
    hbA1c_level: float = 0.0
    blood_glucose_level: int = 0
    diabetes: int = 0
    id_paciente: Optional[str] = None


class ActualizarEntrada(BaseModel):
    gender: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    bmi: Optional[float] = None
    hbA1c_level: Optional[float] = None
    blood_glucose_level: Optional[int] = None
    diabetes: Optional[int] = None
    hypertension: Optional[int] = None
    heart_disease: Optional[int] = None
    id_paciente: Optional[str] = None


@router.get("/estadisticas")
def estadisticas(payload: dict = Depends(require_auth)):
    return _estadisticas()


@router.get("/calidad-diabetes")
def calidad_diabetes(payload: dict = Depends(require_modulo("analisis"))):
    """Indicadores de control DM (HbA1c, glucosa, riesgo) — rol analista / BI."""
    return _calidad_diabetes()


@router.get("/ubicaciones")
def ubicaciones(payload: dict = Depends(require_auth)):
    stats = _estadisticas()
    return sorted(stats.get("ubicaciones", {}).keys())


@router.get("/buscar")
def buscar_registros(
    diabetes: Optional[int] = None,
    gender: Optional[str] = None,
    location: Optional[str] = None,
    age_min: Optional[float] = None,
    age_max: Optional[float] = None,
    payload: dict = Depends(require_modulo("registros")),
):
    filtros = {"diabetes": diabetes, "gender": gender, "location": location,
               "age_min": age_min, "age_max": age_max}
    _auditar(_usuario(payload), "read", f"Búsqueda avanzada: {filtros}")
    return buscar(filtros)


@router.get("/")
def listar_registros(
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    diabetes: Optional[int] = None,
    gender: Optional[str] = None,
    location: Optional[str] = None,
    age_min: Optional[float] = None,
    age_max: Optional[float] = None,
    q: Optional[str] = None,
    payload: dict = Depends(require_modulo("registros")),
):
    filtros = {}
    if diabetes is not None:
        filtros["diabetes"] = diabetes
    if gender:
        filtros["gender"] = gender
    if location:
        filtros["location"] = location
    if age_min is not None:
        filtros["age_min"] = age_min
    if age_max is not None:
        filtros["age_max"] = age_max
    if q:
        filtros["q"] = q.strip()
    if filtros:
        _auditar(_usuario(payload), "read",
                 f"Consulta filtrada ({len(filtros)} criterios), offset={offset}")
    return listar(limit, offset, filtros or None)


@router.get("/{encounter_id}")
def obtener_registro(encounter_id: int, payload: dict = Depends(require_modulo("registros"))):
    return obtener(encounter_id)


@router.post("/")
def crear_registro(datos: RegistroEntrada, payload: dict = Depends(require_modulo("registros"))):
    res = crear(datos.dict())
    if "error" not in res:
        _auditar(_usuario(payload), "create", f"Registro creado id={res.get('encounter_id')}")
    return res


@router.put("/{encounter_id}")
def actualizar_registro(
    encounter_id: int,
    datos: ActualizarEntrada,
    payload: dict = Depends(require_modulo("registros")),
):
    res = actualizar(encounter_id, datos.dict(exclude_none=True))
    if "error" not in res:
        _auditar(_usuario(payload), "update", f"Registro actualizado id={encounter_id}")
    return res


@router.delete("/{encounter_id}")
def eliminar_registro(encounter_id: int, payload: dict = Depends(require_modulo("registros"))):
    res = eliminar(encounter_id)
    if "error" not in res:
        _auditar(_usuario(payload), "delete", f"Registro eliminado id={encounter_id}")
    return res
