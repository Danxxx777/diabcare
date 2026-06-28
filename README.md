# DiabCare Analytics

Plataforma SaaS de análisis clínico de diabetes — 15 paquetes (P1–P15).

## Arranque rápido

```bash
docker compose up -d          # MinIO, PocketBase, Airflow
cd backend
pip install -r requirements.txt
uvicorn Principal:app --reload --port 8000
```

App: http://localhost:8000 — Admin: `admin@diabcare.com` / `Admin2026*`

## Estructura

```
backend/     API FastAPI + servicios por paquete
frontend/    páginas HTML + estaticos/
specs/       especificaciones (requirements, design, tasks)
pruebas/     pytest
ml/          entrenamiento y evaluación ML
```

## Pruebas

```bash
cd backend && py -m pytest ../pruebas/api -q
```
