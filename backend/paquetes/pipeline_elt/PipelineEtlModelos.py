from pydantic import BaseModel, Field


class EjecutarPipelineEntrada(BaseModel):
    historico: bool = False
    run_id: str | None = None
    dag_id: str | None = None


class BenchmarkEntrada(BaseModel):
    max_filas: int | None = Field(default=200_000, ge=1000, le=2_000_000)
