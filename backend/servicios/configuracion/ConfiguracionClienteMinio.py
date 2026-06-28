from minio import Minio
from minio.error import S3Error

MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS = "admin"
MINIO_SECRET = "password123"
MINIO_BUCKET = "diabetes-data"
MINIO_SECURE = False

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
        print(f"[MinIO] Bucket '{MINIO_BUCKET}' listo")
    except S3Error as e:
        print(f"[MinIO] Error: {e}")

def get_cliente():
    return cliente