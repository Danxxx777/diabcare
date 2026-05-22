"""
cargar_a_minio.py
Toma el archivo Parquet más reciente de stage/ y lo sube a MinIO
en el bucket 'diabetes-data' dentro de la carpeta 'stage/'.
"""

import os
import glob
from datetime import datetime
from minio import Minio
from minio.error import S3Error

# ── Configuración ──────────────────────────────────────────────────────────────
MINIO_HOST   = "localhost:9000"
MINIO_ACCESS = "admin"
MINIO_SECRET = "password123"
MINIO_BUCKET = "diabetes-data"
STAGE_DIR    = os.path.join(os.path.dirname(__file__), "..", "stage")

# ── Helpers ────────────────────────────────────────────────────────────────────

def conectar_minio() -> Minio:
    """Crea y retorna el cliente de MinIO."""
    print("🔌 Conectando a MinIO...")
    cliente = Minio(
        MINIO_HOST,
        access_key=MINIO_ACCESS,
        secret_key=MINIO_SECRET,
        secure=False,
    )
    # Verificar que el bucket existe
    if not cliente.bucket_exists(MINIO_BUCKET):
        cliente.make_bucket(MINIO_BUCKET)
        print(f"   Bucket '{MINIO_BUCKET}' creado.")
    else:
        print(f"   Bucket '{MINIO_BUCKET}' encontrado.")
    return cliente


def obtener_parquet_mas_reciente() -> str:
    """Retorna la ruta del archivo Parquet más reciente en stage/."""
    patron  = os.path.join(STAGE_DIR, "diabetes_dataset_*.parquet")
    archivos = sorted(glob.glob(patron), reverse=True)

    if not archivos:
        raise FileNotFoundError(
            f"No se encontró ningún archivo Parquet en: {STAGE_DIR}\n"
            "Ejecuta primero extraer_y_convertir.py"
        )

    ruta = archivos[0]
    print(f"📂 Archivo seleccionado: {os.path.basename(ruta)}")
    return ruta


def subir_a_minio(cliente: Minio, ruta_local: str) -> str:
    """Sube el Parquet a MinIO en la carpeta stage/ y retorna el nombre del objeto."""
    nombre_archivo = os.path.basename(ruta_local)
    nombre_objeto  = f"stage/{nombre_archivo}"
    tam_bytes      = os.path.getsize(ruta_local)
    tam_mb         = tam_bytes / 1_048_576

    print(f"⬆️  Subiendo '{nombre_archivo}' a MinIO ({tam_mb:.2f} MB)...")

    cliente.fput_object(
        bucket_name  = MINIO_BUCKET,
        object_name  = nombre_objeto,
        file_path    = ruta_local,
        content_type = "application/octet-stream",
    )

    url_objeto = f"http://{MINIO_HOST}/{MINIO_BUCKET}/{nombre_objeto}"
    print(f"   Subido correctamente: {url_objeto}")
    return nombre_objeto


def verificar_carga(cliente: Minio, nombre_objeto: str):
    """Verifica que el objeto existe en MinIO tras la carga."""
    try:
        stat = cliente.stat_object(MINIO_BUCKET, nombre_objeto)
        tam_mb = stat.size / 1_048_576
        print(f"✔️  Verificación OK — Tamaño en MinIO: {tam_mb:.2f} MB")
    except S3Error as e:
        print(f"⚠️  No se pudo verificar el objeto: {e}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main(ruta_parquet: str = None):
    """
    Parámetros:
        ruta_parquet: ruta explícita al .parquet. Si no se pasa,
                      se toma el más reciente de stage/.
    """
    print("=" * 60)
    print("  DiabCare — Carga de Parquet a MinIO")
    print("=" * 60)

    if ruta_parquet is None:
        ruta_parquet = obtener_parquet_mas_reciente()

    cliente      = conectar_minio()
    nombre_objeto = subir_a_minio(cliente, ruta_parquet)
    verificar_carga(cliente, nombre_objeto)

    print()
    print("✅ Carga completada.")
    print(f"   Objeto disponible en: {MINIO_BUCKET}/{nombre_objeto}")
    return nombre_objeto


if __name__ == "__main__":
    main()
