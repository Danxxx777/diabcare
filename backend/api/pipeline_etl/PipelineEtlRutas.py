import io
from fastapi import APIRouter, Header
from typing import Optional
from servicios.configuracion.ConfiguracionClienteMinio import get_cliente
from servicios.configuracion.ConfiguracionAjustes import MINIO_BUCKET, MINIO_STAGE_PATH

router = APIRouter(prefix='/api/pipeline', tags=['Pipeline ETL'])


@router.get("/estado")
def estado_pipeline(authorization: Optional[str] = Header(None)):
    try:
        c = get_cliente()
        objetos = list(c.list_objects(MINIO_BUCKET, prefix=MINIO_STAGE_PATH, recursive=True))
        parquets = [o for o in objetos if o.object_name.endswith('.parquet')]
        parquets_sorted = sorted(parquets, key=lambda o: o.last_modified, reverse=True)

        archivos = []
        for obj in parquets_sorted[:10]:
            archivos.append({
                "nombre":       obj.object_name.replace(MINIO_STAGE_PATH, ""),
                "ruta":         obj.object_name,
                "tamano_mb":    round(obj.size / 1024 / 1024, 2),
                "fecha":        obj.last_modified.strftime("%Y-%m-%d %H:%M:%S") if obj.last_modified else "—",
            })

        ultimo = parquets_sorted[0] if parquets_sorted else None

        return {
            "estado":           "activo",
            "bucket":           MINIO_BUCKET,
            "prefix":           MINIO_STAGE_PATH,
            "total_archivos":   len(parquets),
            "ultimo_archivo":   ultimo.object_name.replace(MINIO_STAGE_PATH, "") if ultimo else None,
            "ultima_fecha":     ultimo.last_modified.strftime("%Y-%m-%d %H:%M:%S") if ultimo else None,
            "archivos":         archivos,
        }
    except Exception as e:
        return {"estado": "error", "detalle": str(e)}
