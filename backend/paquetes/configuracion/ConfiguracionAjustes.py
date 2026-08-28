import os

PUERTO_API = int(os.environ.get("DIABCARE_PORT", "8000"))
POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://localhost:8090")
POCKETBASE_EMAIL = os.environ.get("POCKETBASE_EMAIL", "")
POCKETBASE_PASSWORD = os.environ.get("POCKETBASE_PASSWORD", "")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "diabetes-data")
MINIO_STAGE_PATH = os.environ.get("MINIO_STAGE_PATH", "stage/")
POCKETBASE_COLLECTION = os.environ.get("POCKETBASE_COLLECTION", "diabetes_dataset")

# Clave compartida con el DAG de Airflow (header X-DiabCare-Pipeline-Key)
PIPELINE_INTERNAL_KEY = os.environ.get("DIABCARE_PIPELINE_KEY", "diabcare-pipeline-demo")
AIRFLOW_URL = os.environ.get("AIRFLOW_URL", "http://localhost:8081")
AIRFLOW_USER = os.environ.get("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.environ.get("AIRFLOW_PASSWORD", "admin")
AIRFLOW_DAG_ID = os.environ.get("AIRFLOW_DAG_ID", "diabcare_elt")
# Hoja de ruta de DAGs (exhibición académica) — schedule editable también en Airflow UI
AIRFLOW_DAGS = [
    {
        "dag_id": "diabcare_elt",
        "schedule": "@hourly",
        "descripcion": "ELT incremental PocketBase → MinIO (E→L→T)",
        "modo": "incremental",
    },
    {
        "dag_id": "diabcare_elt_historico",
        "schedule": "0 3 * * 0",
        "descripcion": "ELT histórico completo E→L→T (domingos 03:00 UTC)",
        "modo": "historico",
    },
    {
        "dag_id": "diabcare_benchmark_sql",
        "schedule": "@daily",
        "descripcion": "Informe SQL tradicional vs Parquet (tiempos)",
        "modo": "benchmark",
    },
]

# Auth: secreto JWT (obligatorio en prod vía env). No hardcodear en clientes.
JWT_SECRET = os.environ.get("DIABCARE_JWT_SECRET", "diabcare-dev-only-change-me")
JWT_ALGORITMO = os.environ.get("DIABCARE_JWT_ALG", "HS256")
JWT_EXPIRACION_HORAS = int(os.environ.get("DIABCARE_JWT_HOURS", "4"))

# Bootstrap admin@diabcare.com / Admin2026* solo si se habilita explícitamente (demo).
ALLOW_BOOTSTRAP_ADMIN = os.environ.get("DIABCARE_BOOTSTRAP_ADMIN", "1").strip().lower() in (
    "1", "true", "yes", "si", "sí",
)
