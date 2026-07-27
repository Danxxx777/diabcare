# DiabCare Analytics — Punto de entrada principal
# Ejecutar desde backend/:  py -3 Principal.py
# O desde la raíz del repo:  py -3 servidor.py
# Uvicorn:  py -3 -m uvicorn Principal:app --host 0.0.0.0 --port 8000

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from nucleo.utilidades.LogConfig import silenciar_logs, log_advertencia

silenciar_logs()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# API — paquetes P1–P15 + clínico
from paquetes.autenticacion.AutenticacionRutas import router as router_auth
from paquetes.usuarios.UsuariosRutas import router as router_usuarios
from paquetes.registros_clinicos.RegistrosClinicosRutas import router as router_registros
from paquetes.dataset.DatasetRutas import router as router_dataset
from paquetes.prediccion.PrediccionRutas import router as router_prediccion
from paquetes.reportes.ReportesRutas import router as router_reportes
from paquetes.pipeline_elt.PipelineEtlRutas import router as router_pipeline
from paquetes.auditoria.AuditoriaRutas import router as router_auditoria
from paquetes.configuracion.ConfiguracionRutas import router as router_configuracion
from paquetes.modelo_ml.ModeloMlRutas import router as router_modelo_ml
from paquetes.clinico.pacientes.PacientesRutas import router as router_pacientes
from paquetes.clinico.admisiones.AdmisionesRutas import router as router_admisiones
from paquetes.clinico.citas.CitasRutas import router as router_citas
from paquetes.clinico.citas.MisCitasRutas import router as router_mis_citas
from paquetes.notificaciones.NotificacionesRutas import router as router_notificaciones
from paquetes.facturacion.FacturacionRutas import router as router_facturacion
from paquetes.farmacia.FarmaciaRutas import router as router_farmacia
from paquetes.laboratorio.LaboratorioRutas import router as router_laboratorio
from paquetes.urgencias.UrgenciasRutas import router as router_urgencias
from paquetes.comorbilidades.ComorbilidadesRutas import router as router_comorbilidades
from paquetes.rrhh.RrhhRutas import router as router_rrhh

# Infraestructura compartida (P12)
from paquetes.configuracion.ConfiguracionClienteMinio import inicializar_buckets, verificar_conexion
from paquetes.autenticacion.AutenticacionServicio import inicializar_admin
from paquetes.configuracion.ConfiguracionAjustes import PUERTO_API

# ── APP ──
app = FastAPI(
    title="DiabCare Analytics",
    description="DiabCare Hospital — analítica clínica + operación y negocio (P1–P20)",
    version="3.0.0",
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
app.include_router(router_auditoria)
app.include_router(router_configuracion)
app.include_router(router_modelo_ml)
app.include_router(router_pacientes)
app.include_router(router_admisiones)
app.include_router(router_citas)
app.include_router(router_mis_citas)
app.include_router(router_notificaciones)
app.include_router(router_facturacion)
app.include_router(router_farmacia)
app.include_router(router_laboratorio)
app.include_router(router_urgencias)
app.include_router(router_comorbilidades)
app.include_router(router_rrhh)

# ── FRONTEND (HTML vanilla) ──
_BASE = Path(__file__).resolve().parent
_FRONTEND = _BASE.parent / "frontend"

app.mount("/estaticos", StaticFiles(directory=str(_FRONTEND / "estaticos")), name="estaticos")


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(_FRONTEND / "paginas/seguridad/autenticacion/index.html")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    icon = _FRONTEND / "estaticos/img/favicon.ico"
    if icon.is_file():
        return FileResponse(icon, media_type="image/x-icon")
    return FileResponse(_FRONTEND / "estaticos/img/favicon.svg", media_type="image/svg+xml")

# ── HEALTH CHECK ──
@app.get("/api/health", tags=["Sistema"])
def health():
    minio_ok = verificar_conexion()
    return {
        "estado": "ok" if minio_ok else "degradado",
        "minio": "conectado" if minio_ok else "sin conexión",
        "version": "2.0.0-analytics"
    }

# ── STARTUP ──
@app.on_event("startup")
async def startup():
    silenciar_logs()
    try:
        inicializar_buckets()
        inicializar_admin()
    except Exception as e:
        log_advertencia(f"Inicialización incompleta (MinIO?): {e}")
    print("[DiabCare] Servidor activo -> http://localhost:8000  (Ctrl+C para detener)")
    print("[DiabCare] Analytics — paquetes operativos P1–P15")

# ── PÁGINAS HTML ──
# ── REDIRECTS (URLs legacy) ──
from fastapi.responses import RedirectResponse

_LEGACY = {
    "autenticacion/index.html": "seguridad/autenticacion/index.html",
    "usuarios/index.html": "seguridad/usuarios/index.html",
    "perfil/index.html": "seguridad/perfil/index.html",
    "pacientes/index.html": "clinico/pacientes/index.html",
    "admisiones/index.html": "clinico/admisiones/index.html",
    "agenda/index.html": "clinico/agenda/index.html",
    "registros_clinicos/index.html": "clinico/registros_clinicos/index.html",
    "analisis/index.html": "clinico/analisis/index.html",
    "estadisticas/index.html": "clinico/analisis/estadisticas/index.html",
    "analisis/diabetes/index.html": "clinico/analisis/diabetes/index.html",
    "prediccion/index.html": "clinico/prediccion/index.html",
    "reportes/index.html": "clinico/reportes/index.html",
    "dataset/index.html": "datos/dataset/index.html",
    "dataset/generador.html": "datos/dataset/generador.html",
    "pipeline_etl/index.html": "datos/pipeline_elt/index.html",
    "modelo_ml/index.html": "datos/modelo_ml/index.html",
    "auditoria/index.html": "gobierno/auditoria/index.html",
    "configuracion/index.html": "gobierno/configuracion/index.html",
}

@app.get("/paginas/{modulo}/{archivo}", include_in_schema=False)
def pagina_legacy(modulo: str, archivo: str):
    key = f"{modulo}/{archivo}"
    if key in _LEGACY:
        return RedirectResponse(url=f"/paginas/{_LEGACY[key]}", status_code=301)
    return FileResponse(_FRONTEND / "paginas" / modulo / archivo)

@app.get("/paginas/{ruta:path}", include_in_schema=False)
def pagina_archivo(ruta: str):
    return FileResponse(_FRONTEND / "paginas" / ruta)

if __name__ == "__main__":
    import socket
    import subprocess
    import uvicorn

    def _pid_en_puerto(port: int) -> int | None:
        try:
            out = subprocess.check_output(["netstat", "-ano"], text=True, errors="ignore")
        except (OSError, subprocess.CalledProcessError):
            return None
        for line in out.splitlines():
            if f":{port}" in line and "LISTENING" in line.upper():
                parts = line.split()
                if parts:
                    try:
                        return int(parts[-1])
                    except ValueError:
                        pass
        return None

    def _puerto_libre(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return True
            except OSError:
                return False

    if not _puerto_libre(PUERTO_API):
        pid = _pid_en_puerto(PUERTO_API)
        print(f"[DiabCare] ERROR: el puerto {PUERTO_API} ya está en uso.")
        if pid:
            print(f"  Proceso: PID {pid}")
            print(f"  Ciérralo con:  Stop-Process -Id {pid} -Force")
        else:
            print("  Busca el PID con:  netstat -ano | findstr :8000")
        raise SystemExit(1)

    uvicorn.run(
        "Principal:app",
        host="0.0.0.0",
        port=PUERTO_API,
        reload=False,
        log_level="warning",
        access_log=False,
    )
