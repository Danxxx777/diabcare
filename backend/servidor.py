from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

from api.autenticacion.Rutas import enrutador as enrutador_autenticacion
from api.crud.Rutas import enrutador as enrutador_crud
from api.dataset.Rutas import enrutador as enrutador_dataset
from api.prediccion.Rutas import enrutador as enrutador_prediccion
from api.reportes.Rutas import enrutador as enrutador_reportes
from api.usuarios.Rutas import enrutador as enrutador_usuarios
from api.pipeline.Rutas import enrutador as enrutador_pipeline
from api.ml.Rutas import enrutador as enrutador_ml
from api.notificaciones.Rutas import enrutador as enrutador_notificaciones
from api.auditoria.Rutas import enrutador as enrutador_auditoria
from api.benchmarking.Rutas import enrutador as enrutador_benchmarking
from api.configuracion.Rutas import enrutador as enrutador_configuracion
from api.integraciones.Rutas import enrutador as enrutador_integraciones

app = FastAPI(title="DiabCare Analytics")

ruta_estaticos = os.path.join(os.path.dirname(__file__), "..", "frontend", "estaticos")
app.mount("/static", StaticFiles(directory=ruta_estaticos), name="static")

ruta_plantillas = os.path.join(os.path.dirname(__file__), "..", "frontend", "plantillas")
plantillas = Jinja2Templates(directory=ruta_plantillas)

app.include_router(enrutador_autenticacion)
app.include_router(enrutador_crud)
app.include_router(enrutador_dataset)
app.include_router(enrutador_prediccion)
app.include_router(enrutador_reportes)
app.include_router(enrutador_usuarios)
app.include_router(enrutador_pipeline)
app.include_router(enrutador_ml)
app.include_router(enrutador_notificaciones)
app.include_router(enrutador_auditoria)
app.include_router(enrutador_benchmarking)
app.include_router(enrutador_configuracion)
app.include_router(enrutador_integraciones)

@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    return plantillas.TemplateResponse(request, "estructura.html")
