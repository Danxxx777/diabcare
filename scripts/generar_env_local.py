# Genera o regenera `.env` local (NO se sube al git).
# Uso:  py -3 scripts/generar_env_local.py
#
# - Siempre regenera JWT y PIPELINE_KEY
# - Conserva POCKETBASE_* si ya existían en .env
# - Si no hay .env previo, deja POCKETBASE_EMAIL/PASSWORD vacíos para que los completes
from __future__ import annotations

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _leer_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> None:
    prev = _leer_env(ENV_PATH)
    jwt = secrets.token_urlsafe(48)
    pipe = secrets.token_urlsafe(32)
    pb_email = prev.get("POCKETBASE_EMAIL", "")
    pb_pass = prev.get("POCKETBASE_PASSWORD", "")
    content = f"""# DiabCare local — NO subir al git (.gitignore)
# Generado por scripts/generar_env_local.py

DIABCARE_JWT_SECRET={jwt}
DIABCARE_PIPELINE_KEY={pipe}
DIABCARE_BOOTSTRAP_ADMIN={prev.get('DIABCARE_BOOTSTRAP_ADMIN', '1')}
DIABCARE_JWT_HOURS={prev.get('DIABCARE_JWT_HOURS', '4')}
DIABCARE_COOKIE_SECURE={prev.get('DIABCARE_COOKIE_SECURE', '0')}

POCKETBASE_URL={prev.get('POCKETBASE_URL', 'http://localhost:8090')}
POCKETBASE_EMAIL={pb_email}
POCKETBASE_PASSWORD={pb_pass}
POCKETBASE_COLLECTION={prev.get('POCKETBASE_COLLECTION', 'diabetes_dataset')}

MINIO_BUCKET={prev.get('MINIO_BUCKET', 'diabetes-data')}
MINIO_STAGE_PATH={prev.get('MINIO_STAGE_PATH', 'stage/')}

AIRFLOW_URL={prev.get('AIRFLOW_URL', 'http://localhost:8080')}
AIRFLOW_USER={prev.get('AIRFLOW_USER', 'admin')}
AIRFLOW_PASSWORD={prev.get('AIRFLOW_PASSWORD', 'admin')}
AIRFLOW_DAG_ID={prev.get('AIRFLOW_DAG_ID', 'diabcare_elt')}

DIABCARE_PUBLIC_URL={prev.get('DIABCARE_PUBLIC_URL', '')}
STRIPE_SECRET_KEY={prev.get('STRIPE_SECRET_KEY', '')}
STRIPE_PUBLISHABLE_KEY={prev.get('STRIPE_PUBLISHABLE_KEY', '')}
"""
    ENV_PATH.write_text(content, encoding="utf-8")
    print(f"OK: escrito {ENV_PATH}")
    print("  - JWT y PIPELINE_KEY regenerados")
    if pb_email and pb_pass:
        print("  - PocketBase conservado desde .env anterior")
    else:
        print("  - Completa POCKETBASE_EMAIL y POCKETBASE_PASSWORD en .env")
    print("Reinicia con: .\\arrancar.ps1")


if __name__ == "__main__":
    main()
