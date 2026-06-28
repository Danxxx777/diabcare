"""
BenchmarkingServicio — P13 Comparación y benchmarking (departamento Inteligencia
de Negocio). Compara los indicadores reales del sistema contra las metas del
Balanced Scorecard del TA06 (RES-003 de la especificación general):
latencia P95 < 200 ms, uptime >= 99.9%, ELT 600K < 15 min, exactitud >= 96%.
"""

from servicios.prediccion import PrediccionServicio
from servicios.registros_clinicos import RegistrosClinicosServicio


def _pct(valor):
    return None if valor is None else round(float(valor) * 100, 2)


def comparativa() -> dict:
    metricas = PrediccionServicio.obtener_metricas()
    if "error" in metricas:
        metricas = {}

    try:
        stats = RegistrosClinicosServicio.estadisticas()
        total = int(stats.get("total", 0))
    except Exception:
        total = 0

    acc = metricas.get("accuracy")
    prec = metricas.get("precision")
    rec = metricas.get("recall")
    f1 = metricas.get("f1")

    def cumple(valor, umbral):
        return None if valor is None else bool(valor >= umbral)

    indicadores = [
        {"indicador": "Exactitud del modelo (accuracy)", "categoria": "Modelo ML",
         "actual": _pct(acc), "objetivo": ">= 96%", "unidad": "%", "cumple": cumple(acc, 0.96)},
        {"indicador": "Precisión (precision)", "categoria": "Modelo ML",
         "actual": _pct(prec), "objetivo": ">= 90%", "unidad": "%", "cumple": cumple(prec, 0.90)},
        {"indicador": "Sensibilidad (recall)", "categoria": "Modelo ML",
         "actual": _pct(rec), "objetivo": ">= 90%", "unidad": "%", "cumple": cumple(rec, 0.90)},
        {"indicador": "F1-score", "categoria": "Modelo ML",
         "actual": _pct(f1), "objetivo": ">= 90%", "unidad": "%", "cumple": cumple(f1, 0.90)},
        {"indicador": "Tamaño del dataset", "categoria": "Datos",
         "actual": total, "objetivo": "600,000 (ELT)", "unidad": "registros",
         "cumple": (total >= 600000) if total else None},
        {"indicador": "Latencia API (P95)", "categoria": "Operación",
         "actual": None, "objetivo": "< 200 ms", "unidad": "ms", "cumple": None},
        {"indicador": "Disponibilidad (uptime)", "categoria": "Operación",
         "actual": None, "objetivo": ">= 99.9%", "unidad": "%", "cumple": None},
        {"indicador": "Tiempo ELT (600K)", "categoria": "Datos",
         "actual": None, "objetivo": "< 15 min", "unidad": "min", "cumple": None},
    ]

    medibles = [i for i in indicadores if i["cumple"] is not None]
    return {
        "indicadores": indicadores,
        "resumen": {
            "medibles": len(medibles),
            "cumplidos": sum(1 for i in medibles if i["cumple"]),
            "modelo_disponible": PrediccionServicio.modelo_disponible(),
        },
    }
