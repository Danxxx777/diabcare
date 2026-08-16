"""P20 RRHH clínico y costeo."""
from nucleo.utilidades.ParquetStore import ParquetStore

cargos = ParquetStore(
    "negocio/dim_cargo.parquet",
    ["id_cargo", "nombre", "activo", "creado_en", "actualizado_en"],
    "id_cargo", "cargos", modo_borrado="activo",
)
turnos = ParquetStore(
    "negocio/dim_turno.parquet",
    ["id_turno", "nombre", "hora_inicio", "hora_fin", "activo", "creado_en", "actualizado_en"],
    "id_turno", "turnos", modo_borrado="activo",
)
personal = ParquetStore(
    "negocio/oper_personal_costo.parquet",
    ["id_personal_costo", "id_personal", "id_cargo", "costo_hora", "fecha_vigencia",
     "activo", "creado_en", "actualizado_en"],
    "id_personal_costo", "personal", modo_borrado="activo",
)
bridge_turno = ParquetStore(
    "negocio/bridge_personal_turno.parquet",
    ["id_bridge", "id_personal", "id_turno", "fecha", "activo", "creado_en", "actualizado_en"],
    "id_bridge", "asignaciones", modo_borrado="activo",
)
productividad = ParquetStore(
    "negocio/agg_productividad_medica.parquet",
    ["id_agg", "id_personal", "periodo", "num_consultas", "num_procedimientos",
     "ingreso_generado", "creado_en", "actualizado_en"],
    "id_agg", "productividad", modo_borrado="activo",
)

def seed():
    if not (cargos.listar(limit=1).get("cargos") or []):
        for n in ["medico_general", "endocrinologo", "enfermero", "farmaceutico", "administrativo"]:
            cargos.crear({"nombre": n, "activo": True})
    if not (turnos.listar(limit=1).get("turnos") or []):
        for n, hi, hf in [("mañana", "07:00", "15:00"), ("tarde", "15:00", "23:00"), ("noche", "23:00", "07:00")]:
            turnos.crear({"nombre": n, "hora_inicio": hi, "hora_fin": hf, "activo": True})

def costeo() -> dict:
    return personal.listar(limit=200, incluir_inactivos=True)

def productividad_resumen() -> dict:
    return productividad.listar(limit=200, incluir_inactivos=True)


def resumen_operativo() -> dict:
    """Informe simple: personal costeado, turnos y actividad del periodo."""
    _tope = 10**9
    per = personal.listar(limit=_tope, incluir_inactivos=True).get("personal") or []
    asg = bridge_turno.listar(limit=_tope, incluir_inactivos=True).get("asignaciones") or []
    prod = productividad.listar(limit=_tope, incluir_inactivos=True).get("productividad") or []
    costo_prom = round(sum(float(p.get("costo_hora") or 0) for p in per) / len(per), 2) if per else 0.0
    return {
        "tipo": "informe_simple",
        "personal_costeado": len(per),
        "asignaciones_turno": len(asg),
        "costo_hora_promedio": costo_prom,
        "consultas_periodo": int(sum(int(p.get("num_consultas") or 0) for p in prod)),
        "ingreso_generado": round(sum(float(p.get("ingreso_generado") or 0) for p in prod), 2),
    }
