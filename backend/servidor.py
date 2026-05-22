"""
servidor.py — Servidor principal FastAPI de DiabCare Analytics
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

from api.rutas.estadisticas import enrutador as enrutador_estadisticas
from api.rutas.tablas import enrutador as enrutador_tablas
from api.rutas.graficas import enrutador as enrutador_graficas
from api.rutas.empresa import enrutador as enrutador_empresa
from api.rutas.crud_hechos import enrutador as enrutador_crud
from api.rutas.generador import enrutador as enrutador_generador

# ── Aplicación ─────────────────────────────────────────────────────────────────
app = FastAPI(title="DiabCare Analytics")

# ── Archivos estáticos ─────────────────────────────────────────────────────────
ruta_estaticos = os.path.join(os.path.dirname(__file__), "..", "frontend", "estaticos")
app.mount("/static", StaticFiles(directory=ruta_estaticos), name="static")

# ── Plantillas ─────────────────────────────────────────────────────────────────
ruta_plantillas = os.path.join(os.path.dirname(__file__), "..", "frontend", "plantillas")
plantillas = Jinja2Templates(directory=ruta_plantillas)

# ── Rutas ──────────────────────────────────────────────────────────────────────
app.include_router(enrutador_estadisticas)
app.include_router(enrutador_tablas)
app.include_router(enrutador_graficas)
app.include_router(enrutador_empresa)
app.include_router(enrutador_crud)
app.include_router(enrutador_generador)


# ── Página principal ───────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    return plantillas.TemplateResponse(request, "estructura.html")
