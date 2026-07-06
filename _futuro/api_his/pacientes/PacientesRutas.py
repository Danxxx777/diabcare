from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional

from utilidades.Dependencias import require_modulo
from servicios.pacientes.PacientesServicio import (
    listar, obtener, crear, actualizar, eliminar, consultas_paciente, resumen,
    importar_desde_dataset, timeline_paciente, generar_expediente_pdf, evolucion_clinica,
    migrar_formato_legacy, detalle_paciente,
)
from fastapi.responses import Response

router = APIRouter(prefix="/api/pacientes", tags=["Pacientes"])


def _usuario(payload: dict) -> str:
    return (payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


def _auditar(usuario: str, tipo: str, detalle: str):
    try:
        from servicios.auditoria.AuditoriaServicio import registrar
        registrar(usuario, tipo, "pacientes", detalle)
    except Exception:
        pass


class PacienteEntrada(BaseModel):
    nombre: str = Field(min_length=2)
    apellido: str = Field(min_length=2)
    documento: str = Field(min_length=4)
    fecha_nacimiento: str
    genero: str = "Femenino"
    telefono: str = ""
    email: str = ""
    sede: str = "California"
    notas: str = ""


class PacienteActualizar(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    documento: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    genero: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    sede: Optional[str] = None
    estado: Optional[str] = None
    notas: Optional[str] = None


@router.post("/importar-dataset")
def importar_dataset(forzar: bool = False, payload: dict = Depends(require_modulo("pacientes"))):
    res = importar_desde_dataset(forzar=forzar)
    if "error" not in res:
        _auditar(_usuario(payload), "create",
                 f"Importados {res.get('pacientes_nuevos', 0)} pacientes desde dataset")
    return res


@router.post("/migrar-expedientes")
def migrar_expedientes(payload: dict = Depends(require_modulo("pacientes"))):
    res = migrar_formato_legacy()
    if res.get("migrados", 0) > 0:
        _auditar(_usuario(payload), "update", f"Migrados {res['migrados']} expedientes legacy")
    return res


@router.get("/ping")
def ping_pacientes():
    return {"ok": True, "version": "v3-listado-ligero"}


@router.get("/resumen")
def resumen_pacientes(payload: dict = Depends(require_modulo("pacientes"))):
    return resumen()


@router.get("/")
def listar_pacientes(
    q: str = "",
    estado: str = "",
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    payload: dict = Depends(require_modulo("pacientes")),
):
    return listar(q, estado, limit, offset)


@router.get("/{id_paciente}")
def obtener_paciente(id_paciente: str, payload: dict = Depends(require_modulo("pacientes"))):
    return obtener(id_paciente)


@router.get("/{id_paciente}/detalle")
def detalle(
    id_paciente: str,
    consultas: int = Query(25, le=100),
    timeline: int = Query(30, le=80),
    evolucion: int = Query(60, le=120),
    payload: dict = Depends(require_modulo("pacientes")),
):
    return detalle_paciente(id_paciente, consultas, timeline, evolucion)


@router.get("/{id_paciente}/evolucion")
def evolucion(id_paciente: str, limit: int = 120, payload: dict = Depends(require_modulo("pacientes"))):
    return evolucion_clinica(id_paciente, limit)


@router.get("/{id_paciente}/timeline")
def timeline(id_paciente: str, limit: int = 80, payload: dict = Depends(require_modulo("pacientes"))):
    return timeline_paciente(id_paciente, limit)


@router.get("/{id_paciente}/expediente-pdf")
def expediente_pdf(id_paciente: str, payload: dict = Depends(require_modulo("pacientes"))):
    pdf = generar_expediente_pdf(id_paciente)
    if not pdf:
        return {"error": "No se pudo generar el expediente"}
    _auditar(_usuario(payload), "info", f"Expediente PDF id={id_paciente}")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="expediente-{id_paciente[:8]}.pdf"'})


@router.get("/{id_paciente}/consultas")
def consultas(id_paciente: str, limit: int = 50, payload: dict = Depends(require_modulo("pacientes"))):
    return consultas_paciente(id_paciente, limit)


@router.post("/")
def crear_paciente(datos: PacienteEntrada, payload: dict = Depends(require_modulo("pacientes"))):
    res = crear(datos.model_dump())
    if "error" not in res:
        p = res.get("paciente", {})
        _auditar(_usuario(payload), "create",
                 f"Paciente {p.get('codigo_historia')} — {p.get('nombre_completo')}")
    return res


@router.put("/{id_paciente}")
def actualizar_paciente(
    id_paciente: str,
    datos: PacienteActualizar,
    payload: dict = Depends(require_modulo("pacientes")),
):
    res = actualizar(id_paciente, datos.model_dump(exclude_none=True))
    if "error" not in res:
        _auditar(_usuario(payload), "update", f"Paciente actualizado id={id_paciente}")
    return res


@router.delete("/{id_paciente}")
def baja_paciente(id_paciente: str, payload: dict = Depends(require_modulo("pacientes"))):
    res = eliminar(id_paciente)
    if "error" not in res:
        _auditar(_usuario(payload), "delete", f"Paciente baja id={id_paciente}")
    return res
