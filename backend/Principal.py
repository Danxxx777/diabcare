# DiabCare Analytics — Punto de entrada principal
# Ejecutar: uvicorn Principal:app --reload --port 8000

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# API — P1 al P15
from api.autenticacion.AutenticacionRutas import router as router_auth
from api.usuarios.UsuariosRutas import router as router_usuarios
from api.registros_clinicos.RegistrosClinicosRutas import router as router_registros
from api.dataset.DatasetRutas import router as router_dataset
from api.prediccion.PrediccionRutas import router as router_prediccion
from api.reportes.ReportesRutas import router as router_reportes
from api.pipeline_etl.PipelineEtlRutas import router as router_pipeline
from api.notificaciones.NotificacionesRutas import router as router_notificaciones
from api.auditoria.AuditoriaRutas import router as router_auditoria
from api.configuracion.ConfiguracionRutas import router as router_configuracion
from api.benchmarking.BenchmarkingRutas import router as router_benchmarking
from api.modelo_ml.ModeloMlRutas import router as router_modelo_ml
from api.integraciones.IntegracionesRutas import router as router_integraciones

# Servicios de infraestructura
from servicios.configuracion.ConfiguracionClienteMinio import inicializar_buckets, verificar_conexion
from servicios.autenticacion.AutenticacionServicio import inicializar_admin
from servicios.configuracion.ConfiguracionAjustes import PUERTO_API

# ── APP ──
app = FastAPI(
    title="DiabCare Analytics",
    description="Plataforma SaaS de análisis clínico de diabetes hospitalaria",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── RUTAS API ──
app.include_router(router_auth)
app.include_router(router_usuarios)
app.include_router(router_registros)
app.include_router(router_dataset)
app.include_router(router_prediccion)
app.include_router(router_reportes)
app.include_router(router_pipeline)
app.include_router(router_notificaciones)
app.include_router(router_auditoria)
app.include_router(router_configuracion)
app.include_router(router_benchmarking)
app.include_router(router_modelo_ml)
app.include_router(router_integraciones)

# ── FRONTEND ESTÁTICO ──
app.mount("/estaticos", StaticFiles(directory="../frontend/estaticos"), name="estaticos")

@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse("../frontend/paginas/autenticacion/index.html")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)

# ── HEALTH CHECK ──
@app.get("/api/health", tags=["Sistema"])
def health():
    minio_ok = verificar_conexion()
    return {
        "estado": "ok" if minio_ok else "degradado",
        "minio": "conectado" if minio_ok else "sin conexión",
        "version": "2.0.0"
    }

# ── STARTUP ──
@app.on_event("startup")
async def startup():
    print("[DiabCare] Iniciando sistema...")
    inicializar_buckets()
    inicializar_admin()
    print("[DiabCare] Sistema listo en http://localhost:8000")
    print("[DiabCare] Documentación en http://localhost:8000/docs")

# ── PÁGINAS FRONTEND ──
@app.get("/paginas/{modulo}/{archivo}", include_in_schema=False)
def pagina_archivo(modulo: str, archivo: str):
    return FileResponse(f"../frontend/paginas/{modulo}/{archivo}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("Principal:app", host="0.0.0.0", port=PUERTO_API, reload=True)
