from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from utilidades.Dependencias import require_modulo
from servicios.fotos.FotosServicio import (
    listar, subir, leer_binario, eliminar, obtener_principal, TIPOS_ENTIDAD,
)

router = APIRouter(prefix="/api/fotos", tags=["Fotos"])


def _usuario(payload: dict) -> str:
    return payload.get("correo") or payload.get("sub") or payload.get("nombre") or "sistema"


@router.get("/tipos")
def tipos_entidad(payload: dict = Depends(require_modulo("fotos"))):
    return {"tipos": sorted(TIPOS_ENTIDAD)}


@router.get("/entidad/{tipo_entidad}/{id_entidad}")
def listar_fotos(
    tipo_entidad: str,
    id_entidad: str,
    payload: dict = Depends(require_modulo("fotos")),
):
    return listar(tipo_entidad, id_entidad)


@router.get("/entidad/{tipo_entidad}/{id_entidad}/principal")
def foto_principal(
    tipo_entidad: str,
    id_entidad: str,
    payload: dict = Depends(require_modulo("fotos")),
):
    f = obtener_principal(tipo_entidad, id_entidad)
    if not f:
        return {"foto": None}
    return {"foto": f}


@router.post("/")
async def cargar_foto(
    tipo_entidad: str = Form(...),
    id_entidad: str = Form(...),
    es_principal: bool = Form(True),
    archivo: UploadFile = File(...),
    payload: dict = Depends(require_modulo("fotos")),
):
    contenido = await archivo.read()
    return subir(
        tipo_entidad=tipo_entidad,
        id_entidad=id_entidad,
        contenido=contenido,
        mime_type=archivo.content_type or "application/octet-stream",
        nombre_archivo=archivo.filename or "foto.jpg",
        subido_por=_usuario(payload),
        es_principal=es_principal,
    )


@router.get("/{id_foto}/imagen")
def servir_imagen(id_foto: str, payload: dict = Depends(require_modulo("fotos"))):
    res = leer_binario(id_foto)
    if not res:
        return Response(status_code=404, content="Foto no encontrada")
    data, mime = res
    return Response(content=data, media_type=mime)


@router.delete("/{id_foto}")
def borrar_foto(id_foto: str, payload: dict = Depends(require_modulo("fotos"))):
    return eliminar(id_foto)
