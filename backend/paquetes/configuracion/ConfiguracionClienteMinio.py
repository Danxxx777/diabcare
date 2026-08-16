import os

from minio import Minio
from minio.error import S3Error

# Las credenciales salen del entorno (.env, ignorado por git). Estaban escritas
# aqui en texto plano y este archivo si esta versionado, asi que el par quedaba
# publicado en el repositorio. Los valores por defecto son los del MinIO local
# de desarrollo: en cualquier despliegue real hay que definir las variables.
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS = os.getenv("MINIO_ROOT_USER", "admin")
MINIO_SECRET = os.getenv("MINIO_ROOT_PASSWORD", "password123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "diabetes-data")
MINIO_SECURE = os.getenv("MINIO_SECURE", "0").strip().lower() in ("1", "true", "yes")

from nucleo.utilidades.LogConfig import log_advertencia

cliente = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=MINIO_SECURE)

def verificar_conexion() -> bool:
    try:
        cliente.list_buckets()
        return True
    except Exception:
        return False

def inicializar_buckets():
    try:
        if not cliente.bucket_exists(MINIO_BUCKET):
            cliente.make_bucket(MINIO_BUCKET)
    except S3Error as e:
        log_advertencia(f"MinIO: {e}")

def get_cliente():
    return cliente