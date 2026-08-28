import csv
import io

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from typing import Optional
from nucleo.utilidades.Dependencias import require_modulo, require_escritura
from paquetes.rrhh import RrhhServicio as S

router = APIRouter(prefix="/api/rrhh", tags=["P20 RRHH"])

def _u(p): return p.get("correo") or p.get("email") or p.get("sub") or "sistema"
def _ok(r):
    if r.get("error"): raise HTTPException(400, detail=r["error"])
    return r
def _nf(r):
    if r.get("error"): raise HTTPException(404, detail=r["error"])
    return r

class CargoIn(BaseModel):
    nombre: str = ""
    activo: Optional[bool] = True

class TurnoIn(BaseModel):
    nombre: str = ""
    hora_inicio: str = ""
    hora_fin: str = ""
    activo: Optional[bool] = True

class PersonalIn(BaseModel):
    id_personal: str
    id_cargo: str
    costo_hora: float = Field(0, ge=0)
    fecha_vigencia: str = ""
    activo: Optional[bool] = True

class EmpleadoIn(BaseModel):
    codigo: str
    nombre: str
    apellido: str = ""
    documento: str = ""
    email: str = ""
    telefono: str = ""
    cargo: str = ""
    area: str = ""
    sede: str = ""
    fecha_ingreso: str = ""
    estado_laboral: str = "activo"
    rol_sugerido: str = ""

class ProvisionarIn(BaseModel):
    ids: list[str]

class AsignacionTurnoIn(BaseModel):
    id_personal: str
    id_turno: str
    fecha: str
    activo: Optional[bool] = True

@router.get("/empleados")
def list_empleados(offset: int = 0, limit: int = 100, payload=Depends(require_modulo("rrhh"))):
    return S.listar_empleados(offset, min(limit, 500))

@router.get("/empleados/resumen")
def resumen_empleados(payload=Depends(require_modulo("rrhh"))):
    return S.resumen_empleados()

@router.post("/empleados")
def post_empleado(d: EmpleadoIn, payload=Depends(require_escritura("rrhh"))):
    r = _ok(S.crear_empleado(d.dict()))
    S.empleados.auditar(_u(payload), "create", f"Empleado {r.get('id_empleado')}", "rrhh")
    return r

@router.put("/empleados/{id_empleado}")
def put_empleado(id_empleado: str, d: EmpleadoIn, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.actualizar_empleado(id_empleado, d.dict()))
    S.empleados.auditar(_u(payload), "update", f"Empleado {id_empleado}", "rrhh")
    return r

@router.post("/empleados/provisionar")
def provisionar_empleados(d: ProvisionarIn, payload=Depends(require_escritura("rrhh"))):
    return _ok(S.provisionar_empleados(d.ids, _u(payload)))

@router.get("/asignaciones")
def list_asignaciones(offset: int = 0, limit: int = 100, payload=Depends(require_modulo("rrhh"))):
    return S.bridge_turno.listar(offset, min(limit, 500), incluir_inactivos=True)

@router.post("/asignaciones")
def post_asignacion(d: AsignacionTurnoIn, payload=Depends(require_escritura("rrhh"))):
    r = _ok(S.crear_asignacion(d.dict()))
    S.bridge_turno.auditar(_u(payload), "create", f"Asignación {r.get('id_bridge')}", "rrhh")
    return r

@router.put("/asignaciones/{id_bridge}")
def put_asignacion(id_bridge: str, d: AsignacionTurnoIn, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.bridge_turno.actualizar(id_bridge, d.dict()))
    S.bridge_turno.auditar(_u(payload), "update", f"Asignación {id_bridge}", "rrhh")
    return r

@router.delete("/asignaciones/{id_bridge}")
def del_asignacion(id_bridge: str, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.bridge_turno.eliminar_logico(id_bridge))
    S.bridge_turno.auditar(_u(payload), "delete", f"Asignación {id_bridge}", "rrhh")
    return r

@router.post("/empleados/importar")
async def importar_empleados(
    archivo: UploadFile = File(...), payload=Depends(require_escritura("rrhh"))
):
    contenido = await archivo.read()
    if len(contenido) > 5 * 1024 * 1024:
        raise HTTPException(413, detail="El archivo supera el límite de 5 MB")
    nombre = (archivo.filename or "").lower()
    if nombre.endswith(".xlsx"):
        try:
            hoja = pd.read_excel(io.BytesIO(contenido), sheet_name="Empleados", header=None, dtype=str)
            encabezado = next(
                (i for i, row in hoja.head(10).iterrows()
                 if "codigo" in {S._clave(v) for v in row.tolist()} and "nombre" in {S._clave(v) for v in row.tolist()}),
                None,
            )
            if encabezado is None:
                raise ValueError("No se encontraron las columnas Código y Nombre")
            datos = hoja.iloc[encabezado + 1:].copy()
            datos.columns = hoja.iloc[encabezado].tolist()
            datos = datos.dropna(how="all").fillna("")
            filas = datos.to_dict(orient="records")
        except (ValueError, ImportError) as exc:
            raise HTTPException(400, detail=f"Excel inválido: {exc}") from exc
    else:
        try:
            texto = contenido.decode("utf-8-sig")
            muestra = texto[:4096]
            dialecto = csv.Sniffer().sniff(muestra, delimiters=",;")
            filas = list(csv.DictReader(io.StringIO(texto), dialect=dialecto))
        except (UnicodeDecodeError, csv.Error) as exc:
            raise HTTPException(400, detail="CSV inválido o codificación distinta de UTF-8") from exc
    if len(filas) > 10000:
        raise HTTPException(400, detail="Máximo 10.000 empleados por archivo")
    resultado = S.importar_empleados(filas)
    S.empleados.auditar(_u(payload), "import", f"Archivo RRHH: {len(filas)} filas", "rrhh")
    return resultado

@router.get("/colaboradores")
def colaboradores(payload=Depends(require_modulo("rrhh"))):
    """Catálogo legible de personal (sin pedir IDs a mano en UI)."""
    from paquetes.usuarios.UsuariosServicio import obtener_usuarios
    rows = obtener_usuarios()
    if isinstance(rows, list):
        return {
            "colaboradores": [
                {
                    "id": u.get("id"),
                    "nombre": u.get("nombre") or u.get("email") or "Usuario",
                    "rol": u.get("rol") or "",
                    "activo": u.get("activo", True),
                }
                for u in rows
                if str(u.get("activo", True)).lower() not in ("false", "0", "no")
            ]
        }
    return {"colaboradores": []}


@router.get("/cargos")
def list_cargos(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("rrhh"))):
    return S.cargos.listar(offset, limit, incluir_inactivos=True)

@router.get("/cargos/{id_cargo}")
def get_cargo(id_cargo: str, payload=Depends(require_modulo("rrhh"))):
    return _nf(S.cargos.obtener(id_cargo))

@router.post("/cargos")
def post_cargo(d: CargoIn, payload=Depends(require_escritura("rrhh"))):
    r = _ok(S.cargos.crear(d.dict()))
    S.cargos.auditar(_u(payload), "create", f"Cargo {r.get('id_cargo')}", "rrhh"); return r

@router.put("/cargos/{id_cargo}")
def put_cargo(id_cargo: str, d: CargoIn, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.cargos.actualizar(id_cargo, d.dict(exclude_none=True)))
    S.cargos.auditar(_u(payload), "update", f"Cargo {id_cargo}", "rrhh"); return r

@router.delete("/cargos/{id_cargo}")
def del_cargo(id_cargo: str, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.cargos.eliminar_logico(id_cargo))
    S.cargos.auditar(_u(payload), "delete", f"Cargo {id_cargo}", "rrhh"); return r

@router.get("/turnos")
def list_turnos(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("rrhh"))):
    return S.turnos.listar(offset, limit, incluir_inactivos=True)

@router.get("/turnos/{id_turno}")
def get_turno(id_turno: str, payload=Depends(require_modulo("rrhh"))):
    return _nf(S.turnos.obtener(id_turno))

@router.post("/turnos")
def post_turno(d: TurnoIn, payload=Depends(require_escritura("rrhh"))):
    r = _ok(S.turnos.crear(d.dict()))
    S.turnos.auditar(_u(payload), "create", f"Turno {r.get('id_turno')}", "rrhh"); return r

@router.put("/turnos/{id_turno}")
def put_turno(id_turno: str, d: TurnoIn, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.turnos.actualizar(id_turno, d.dict(exclude_none=True)))
    S.turnos.auditar(_u(payload), "update", f"Turno {id_turno}", "rrhh"); return r

@router.delete("/turnos/{id_turno}")
def del_turno(id_turno: str, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.turnos.eliminar_logico(id_turno))
    S.turnos.auditar(_u(payload), "delete", f"Turno {id_turno}", "rrhh"); return r

@router.get("/personal")
def list_per(offset: int = 0, limit: int = 50, payload=Depends(require_modulo("rrhh"))):
    return S.personal.listar(offset, limit, incluir_inactivos=True)

@router.get("/personal/{id_personal_costo}")
def get_per(id_personal_costo: str, payload=Depends(require_modulo("rrhh"))):
    return _nf(S.personal.obtener(id_personal_costo))

@router.post("/personal")
def post_per(d: PersonalIn, payload=Depends(require_escritura("rrhh"))):
    r = _ok(S.personal.crear(d.dict()))
    S.personal.auditar(_u(payload), "create", f"Personal {r.get('id_personal_costo')}", "rrhh"); return r

@router.put("/personal/{id_personal_costo}")
def put_per(id_personal_costo: str, d: PersonalIn, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.personal.actualizar(id_personal_costo, d.dict(exclude_none=True)))
    S.personal.auditar(_u(payload), "update", f"Personal {id_personal_costo}", "rrhh"); return r

@router.delete("/personal/{id_personal_costo}")
def del_per(id_personal_costo: str, payload=Depends(require_escritura("rrhh"))):
    r = _nf(S.personal.eliminar_logico(id_personal_costo))
    S.personal.auditar(_u(payload), "delete", f"Personal {id_personal_costo}", "rrhh"); return r

@router.get("/costeo")
def costeo(payload=Depends(require_modulo("rrhh"))):
    return S.costeo()

@router.get("/productividad")
def prod(payload=Depends(require_modulo("rrhh"))):
    return S.productividad_resumen()

@router.get("/resumen")
def resumen(payload=Depends(require_modulo("rrhh"))):
    return S.resumen_operativo()

@router.post("/seed")
def seed(payload=Depends(require_escritura("rrhh"))):
    S.seed(); return {"mensaje": "seed rrhh ok"}
