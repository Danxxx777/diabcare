from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Header, Request
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import base64
import io
import secrets
import time

from nucleo.utilidades.Dependencias import require_modulo, auth_desde_request, PERMISOS_MODULOS
from paquetes.clinico.pacientes.PacientesServicio import (
    resumen, listar, obtener, crear, actualizar, eliminar,
)
from paquetes.registros_clinicos.RegistrosClinicosServicio import listar_por_paciente

router = APIRouter(prefix="/api/pacientes", tags=["Pacientes"])
_foto_movil: dict[str, dict] = {}


def _limpiar_fotos_moviles() -> None:
    ahora = time.time()
    for token in [k for k, v in _foto_movil.items() if ahora - v.get("creado", 0) > 900]:
        _foto_movil.pop(token, None)


def _usuario(payload: dict) -> str:
    return payload.get("correo") or payload.get("sub") or payload.get("nombre") or "sistema"


def _auditar(usuario: str, tipo: str, detalle: str):
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, tipo, "pacientes", detalle)
    except Exception:
        pass


def _auth_foto(
    request: Request,
    authorization: str = Header(None),
    token: str = Query(None),
) -> dict:
    """Cookie httpOnly, Authorization o ?token= (legacy para <img src>)."""
    payload = auth_desde_request(request, authorization, token_query=token)
    roles = PERMISOS_MODULOS.get("pacientes", ["administrador"])
    if payload.get("rol") not in roles:
        raise HTTPException(status_code=403, detail="Sin acceso al módulo pacientes")
    return payload


class PacienteEntrada(BaseModel):
    nombre: str
    apellido: str = ""
    documento: str = ""
    edad: float = 0
    genero: str = "Femenino"
    telefono: str = ""
    email: str = ""
    sede: str = "Sede principal"
    notas: str = ""
    codigo: Optional[str] = None


class PacienteActualizar(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    documento: Optional[str] = None
    edad: Optional[float] = None
    genero: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    sede: Optional[str] = None
    estado: Optional[str] = None
    notas: Optional[str] = None


@router.post("/foto-movil/sesiones")
def crear_sesion_foto_movil(request: Request, payload: dict = Depends(require_modulo("pacientes"))):
    from nucleo.utilidades.UrlPublica import base_publica, alcance_url
    import qrcode

    _limpiar_fotos_moviles()
    token = secrets.token_urlsafe(24)
    _foto_movil[token] = {"creado": time.time(), "contenido": None, "mime_type": ""}
    base = base_publica(str(request.base_url).rstrip("/"))
    url = f"{base}/paginas/clinico/pacientes/foto-movil.html?token={token}"
    qr = qrcode.QRCode(version=3, box_size=5, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    salida = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(salida, format="PNG")
    return {
        "token": token,
        "url": url,
        "qr_png": "data:image/png;base64," + base64.b64encode(salida.getvalue()).decode("ascii"),
        "alcance": alcance_url(base),
    }


@router.post("/foto-movil/{token}")
async def recibir_foto_movil(token: str, archivo: UploadFile = File(...)):
    _limpiar_fotos_moviles()
    sesion = _foto_movil.get(token)
    if not sesion:
        raise HTTPException(status_code=404, detail="Enlace vencido")
    contenido = await archivo.read()
    if not contenido or len(contenido) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Foto vacía o mayor a 8 MB")
    mime = archivo.content_type or "image/jpeg"
    if mime not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Formato de imagen no permitido")
    sesion.update({"contenido": contenido, "mime_type": mime})
    return {"mensaje": "Foto recibida"}


@router.get("/foto-movil/{token}/estado")
def estado_foto_movil(token: str, payload: dict = Depends(require_modulo("pacientes"))):
    _limpiar_fotos_moviles()
    sesion = _foto_movil.get(token)
    if not sesion:
        raise HTTPException(status_code=404, detail="Enlace vencido")
    contenido = sesion.get("contenido")
    return {
        "recibida": bool(contenido),
        "foto": (f"data:{sesion['mime_type']};base64," + base64.b64encode(contenido).decode("ascii")) if contenido else "",
    }


@router.post("/foto-movil/{token}/asignar/{id_paciente}")
def asignar_foto_movil(token: str, id_paciente: str, payload: dict = Depends(require_modulo("pacientes"))):
    from paquetes.clinico.pacientes.FotosEntidadServicio import guardar_foto
    _limpiar_fotos_moviles()
    sesion = _foto_movil.get(token)
    if not sesion or not sesion.get("contenido"):
        raise HTTPException(status_code=400, detail="El celular todavía no envió la foto")
    if "error" in obtener(id_paciente):
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    res = guardar_foto("paciente", id_paciente, sesion["contenido"], sesion["mime_type"], _usuario(payload))
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res["error"])
    _foto_movil.pop(token, None)
    return res


@router.get("/resumen")
def resumen_pacientes(payload: dict = Depends(require_modulo("pacientes"))):
    return resumen()


@router.post("/fotos/automaticas")
def fotos_automaticas(
    limite: int = Query(200, ge=1, le=2000),
    solo_sin_foto: bool = Query(True),
    payload: dict = Depends(require_modulo("pacientes")),
):
    """Asigna retratos demo (randomuser.me) a pacientes sin foto. No scrapea Pinterest."""
    from paquetes.clinico.pacientes.FotosEntidadServicio import asignar_fotos_automaticas

    res = asignar_fotos_automaticas(
        limite=limite,
        solo_sin_foto=solo_sin_foto,
        usuario=_usuario(payload),
    )
    _auditar(
        _usuario(payload),
        "update",
        f"Fotos automáticas: {res.get('asignadas', 0)} asignadas / {res.get('candidatos', 0)} candidatos",
    )
    return res


@router.get("/")
def listar_pacientes(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: str = "",
    estado: str = "",
    payload: dict = Depends(require_modulo("pacientes")),
):
    return listar(offset, limit, q, estado)


@router.get("/{id_paciente}/consultas")
def consultas_paciente(
    id_paciente: str,
    limit: int = Query(50, ge=1, le=200),
    payload: dict = Depends(require_modulo("pacientes")),
):
    p = obtener(id_paciente)
    if "error" in p:
        raise HTTPException(status_code=404, detail=p["error"])
    return listar_por_paciente(id_paciente, limit)


@router.get("/{id_paciente}/foto")
def foto_paciente(id_paciente: str, payload: dict = Depends(_auth_foto)):
    from paquetes.clinico.pacientes.FotosEntidadServicio import leer_bytes_foto

    p = obtener(id_paciente)
    if "error" in p:
        raise HTTPException(status_code=404, detail=p["error"])
    res = leer_bytes_foto("paciente", id_paciente)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res["error"])
    return Response(content=res["contenido"], media_type=res["mime_type"])


@router.post("/{id_paciente}/foto")
async def subir_foto_paciente(
    id_paciente: str,
    archivo: UploadFile = File(...),
    payload: dict = Depends(require_modulo("pacientes")),
):
    from paquetes.clinico.pacientes.FotosEntidadServicio import guardar_foto

    p = obtener(id_paciente)
    if "error" in p:
        raise HTTPException(status_code=404, detail=p["error"])
    contenido = await archivo.read()
    res = guardar_foto(
        "paciente",
        id_paciente,
        contenido,
        archivo.content_type or "image/jpeg",
        _usuario(payload),
    )
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res["error"])
    _auditar(_usuario(payload), "update", f"Foto paciente {id_paciente}")
    return res


@router.get("/{id_paciente}")
def obtener_paciente(id_paciente: str, payload: dict = Depends(require_modulo("pacientes"))):
    res = obtener(id_paciente)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/")
def crear_paciente(datos: PacienteEntrada, payload: dict = Depends(require_modulo("pacientes"))):
    res = crear(datos.dict())
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    _auditar(_usuario(payload), "create", f"Paciente {res.get('id_paciente')}")
    return res


@router.put("/{id_paciente}")
def editar_paciente(
    id_paciente: str,
    datos: PacienteActualizar,
    payload: dict = Depends(require_modulo("pacientes")),
):
    res = actualizar(id_paciente, datos.dict(exclude_none=True))
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    _auditar(_usuario(payload), "update", f"Paciente {id_paciente}")
    return res


@router.delete("/{id_paciente}")
def eliminar_paciente(id_paciente: str, payload: dict = Depends(require_modulo("pacientes"))):
    res = eliminar(id_paciente)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    _auditar(_usuario(payload), "delete", f"Paciente {id_paciente} eliminado")
    return res
