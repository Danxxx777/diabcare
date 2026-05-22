"""
pipeline_diabetes.py — DAG de Airflow que orquesta y valida el pipeline ETL
Flujo: PocketBase -> Parquet (stage/) -> MinIO
Airflow solo valida que cada paso se complete correctamente.
"""

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
import subprocess
import sys
import os

RUTA_SCRIPTS = "/opt/airflow/dags/scripts"

argumentos_default = {
    "owner": "loor",
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
}

dag = DAG(
    "pipeline_diabetes",
    default_args=argumentos_default,
    description="Orquesta y valida: PocketBase -> Parquet -> MinIO",
    schedule_interval=None,
    catchup=False,
)


def validar_extraccion_y_conversion(**kwargs):
    """Ejecuta extraer_y_convertir.py y valida que se genere el Parquet en stage/."""
    script = os.path.join(RUTA_SCRIPTS, "extraer_y_convertir.py")
    resultado = subprocess.run(
        [sys.executable, script],
        capture_output=True, text=True, timeout=600
    )
    print(resultado.stdout)
    if resultado.returncode != 0:
        raise Exception(f"Error en extraccion: {resultado.stderr}")

    # Validar que existe el Parquet en stage/
    import glob
    archivos = glob.glob("/opt/airflow/stage/*.parquet")
    if not archivos:
        raise Exception("No se genero el archivo Parquet en stage/")

    mas_reciente = max(archivos, key=os.path.getmtime)
    print(f"Validado: {mas_reciente}")
    kwargs["ti"].xcom_push(key="parquet_path", value=mas_reciente)


def validar_carga_minio(**kwargs):
    """Ejecuta cargar_a_minio.py y valida que el archivo este en MinIO."""
    script = os.path.join(RUTA_SCRIPTS, "cargar_a_minio.py")
    resultado = subprocess.run(
        [sys.executable, script],
        capture_output=True, text=True, timeout=120
    )
    print(resultado.stdout)
    if resultado.returncode != 0:
        raise Exception(f"Error al cargar a MinIO: {resultado.stderr}")

    # Validar que MinIO tiene el archivo
    from minio import Minio
    cliente = Minio("host.docker.internal:9000", access_key="admin", secret_key="password123", secure=False)
    objetos = list(cliente.list_objects("diabetes-data", prefix="stage/"))
    parquets = [o for o in objetos if o.object_name.endswith(".parquet")]
    if not parquets:
        raise Exception("El archivo Parquet no se encontro en MinIO stage/")

    print(f"Validado en MinIO: {len(parquets)} archivo(s) en stage/")


tarea_1 = PythonOperator(
    task_id="extraer_convertir_validar",
    python_callable=validar_extraccion_y_conversion,
    provide_context=True,
    dag=dag,
)

tarea_2 = PythonOperator(
    task_id="cargar_minio_validar",
    python_callable=validar_carga_minio,
    provide_context=True,
    dag=dag,
)

tarea_1 >> tarea_2
