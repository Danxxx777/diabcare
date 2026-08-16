from fastapi import APIRouter, Depends, Header, HTTPException

from nucleo.utilidades.Dependencias import require_modulo
from paquetes.configuracion.ConfiguracionAjustes import PIPELINE_INTERNAL_KEY
from paquetes.pipeline_elt.PipelineEtlModelos import EjecutarPipelineEntrada, BenchmarkEntrada
from paquetes.pipeline_elt.PipelineEtlServicio import (
    obtener_estado,
    ejecutar_elt,
    estado_publico,
    estado_airflow,
    disparar_airflow,
    listar_dags_configurados,
)
from paquetes.pipeline_elt.PipelineEtlPasos import (
    paso_extraer,
    paso_transformar,
    paso_cargar,
    correr_benchmark,
    leer_benchmark_ultimo,
    leer_ultima_corrida,
    nuevo_run_id,
)

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline ELT"])


def _usuario(payload: dict) -> str:
    return (payload.get("email") or payload.get("correo") or payload.get("sub")
            or payload.get("nombre") or "sistema")


def _validar_clave_interna(x_diabcare_pipeline_key: str | None) -> None:
    if not x_diabcare_pipeline_key or x_diabcare_pipeline_key != PIPELINE_INTERNAL_KEY:
        raise HTTPException(status_code=401, detail="Clave de pipeline inválida")


@router.get("/estado")
def estado_pipeline(payload: dict = Depends(require_modulo("pipeline_etl"))):
    data = obtener_estado()
    data["airflow"] = estado_airflow()
    return data


@router.get("/estado-publico")
def estado_pipeline_publico():
    """Sin JWT — usado por el healthcheck del DAG Airflow."""
    return estado_publico()


@router.get("/airflow")
def airflow_info(payload: dict = Depends(require_modulo("pipeline_etl"))):
    return estado_airflow()


@router.get("/dags")
def dags_lista(payload: dict = Depends(require_modulo("pipeline_etl"))):
    """Hoja de ruta de DAGs (cuál ejecutar y cada cuánto)."""
    af = estado_airflow()
    return {
        "ok": True,
        "dags": af.get("dags") or listar_dags_configurados(),
        "airflow_conectado": af.get("conectado"),
        "estrategia_carga": (
            "ELT E→L→T: crudo a landing/, luego transform a stage/+DWH. "
            "Incremental (no borra). Histórico relee PocketBase completo."
        ),
    }


@router.post("/ejecutar")
def ejecutar_pipeline(
    datos: EjecutarPipelineEntrada | None = None,
    payload: dict = Depends(require_modulo("pipeline_etl")),
):
    historico = bool((datos or EjecutarPipelineEntrada()).historico)
    return ejecutar_elt(_usuario(payload), historico=historico)


@router.post("/ejecutar-interno")
def ejecutar_pipeline_interno(
    datos: EjecutarPipelineEntrada | None = None,
    x_diabcare_pipeline_key: str | None = Header(default=None, alias="X-DiabCare-Pipeline-Key"),
):
    """Invocado por Airflow (clave compartida, sin JWT de usuario) — pipeline completo."""
    _validar_clave_interna(x_diabcare_pipeline_key)
    body = datos or EjecutarPipelineEntrada()
    return ejecutar_elt("airflow", historico=bool(body.historico))


@router.post("/ejecutar-interno/extraer")
def ejecutar_extraer_interno(
    datos: EjecutarPipelineEntrada | None = None,
    x_diabcare_pipeline_key: str | None = Header(default=None, alias="X-DiabCare-Pipeline-Key"),
):
    _validar_clave_interna(x_diabcare_pipeline_key)
    body = datos or EjecutarPipelineEntrada()
    return paso_extraer(historico=bool(body.historico), run_id=body.run_id or nuevo_run_id())


@router.post("/ejecutar-interno/cargar")
def ejecutar_cargar_interno(
    datos: EjecutarPipelineEntrada | None = None,
    x_diabcare_pipeline_key: str | None = Header(default=None, alias="X-DiabCare-Pipeline-Key"),
):
    """L — carga crudo a MinIO landing/ (antes de transformar)."""
    _validar_clave_interna(x_diabcare_pipeline_key)
    body = datos or EjecutarPipelineEntrada()
    if not body.run_id:
        raise HTTPException(status_code=400, detail="run_id requerido")
    return paso_cargar(run_id=body.run_id)


@router.post("/ejecutar-interno/transformar")
def ejecutar_transformar_interno(
    datos: EjecutarPipelineEntrada | None = None,
    x_diabcare_pipeline_key: str | None = Header(default=None, alias="X-DiabCare-Pipeline-Key"),
):
    """T — normaliza landing → stage/ + materializa DWH."""
    _validar_clave_interna(x_diabcare_pipeline_key)
    body = datos or EjecutarPipelineEntrada()
    if not body.run_id:
        raise HTTPException(status_code=400, detail="run_id requerido")
    return paso_transformar(run_id=body.run_id, materializar=True)


@router.post("/airflow/disparar")
def airflow_disparar(
    datos: EjecutarPipelineEntrada | None = None,
    payload: dict = Depends(require_modulo("pipeline_etl")),
):
    """Crea un dagRun en Apache Airflow (orquestación)."""
    body = datos or EjecutarPipelineEntrada()
    return disparar_airflow(historico=bool(body.historico), dag_id=body.dag_id)


@router.post("/benchmark-sql")
def benchmark_sql(
    datos: BenchmarkEntrada | None = None,
    payload: dict = Depends(require_modulo("pipeline_etl")),
):
    """Informe tradicional SQL (SQLite) vs columnar Parquet — tiempos comparados."""
    max_filas = (datos or BenchmarkEntrada()).max_filas
    return correr_benchmark(max_filas=max_filas)


@router.post("/benchmark-sql-interno")
def benchmark_sql_interno(
    datos: BenchmarkEntrada | None = None,
    x_diabcare_pipeline_key: str | None = Header(default=None, alias="X-DiabCare-Pipeline-Key"),
):
    _validar_clave_interna(x_diabcare_pipeline_key)
    max_filas = (datos or BenchmarkEntrada()).max_filas
    return correr_benchmark(max_filas=max_filas)


@router.get("/benchmark-sql")
def benchmark_sql_ultimo(payload: dict = Depends(require_modulo("pipeline_etl"))):
    b = leer_benchmark_ultimo()
    if not b:
        return {"ok": False, "mensaje": "Aún no hay benchmark. Ejecute POST /api/pipeline/benchmark-sql"}
    return b


@router.get("/ultima-corrida")
def ultima_corrida_elt(payload: dict = Depends(require_modulo("pipeline_etl"))):
    return {"ok": True, "corrida": leer_ultima_corrida() or {}}
