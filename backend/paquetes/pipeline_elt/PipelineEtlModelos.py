from pydantic import BaseModel
class EjecutarPipelineEntrada(BaseModel):
    historico: bool = False
