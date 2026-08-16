"""Validaciones clínicas compartidas (fechas, horario de consulta)."""
from __future__ import annotations

from datetime import datetime, time


HORARIO_CONSULTA_INICIO = time(7, 0)
HORARIO_CONSULTA_FIN = time(19, 0)
# 0=lunes … 6=domingo. Domingo no hay consulta programada (urgencias sí).
DIAS_CONSULTA = {0, 1, 2, 3, 4, 5}


def rango_fechas_ok(inicio: str, fin: str) -> str:
    """Vacío si el rango es válido; mensaje de error si no."""
    a = str(inicio or "").strip()[:10]
    b = str(fin or "").strip()[:10]
    if not a or not b:
        return ""
    try:
        da = datetime.strptime(a, "%Y-%m-%d").date()
        db = datetime.strptime(b, "%Y-%m-%d").date()
    except ValueError:
        return "Las fechas no tienen un formato válido (AAAA-MM-DD)."
    if db < da:
        return "La fecha final no puede ser anterior a la fecha inicial."
    return ""


def parse_hora(valor: str) -> time | None:
    s = str(valor or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s[:8], fmt).time()
        except ValueError:
            continue
    return None


def horario_consulta_ok(fecha: str, hora: str) -> str:
    """Vacío si el turno cabe en el horario de consulta; si no, el motivo."""
    f = str(fecha or "").strip()[:10]
    h = parse_hora(hora)
    if not f:
        return "Indique la fecha del turno."
    if h is None:
        return "Indique una hora válida."
    try:
        dia = datetime.strptime(f, "%Y-%m-%d").date()
    except ValueError:
        return "La fecha no es válida."
    if dia.weekday() not in DIAS_CONSULTA:
        return "No hay consulta programada los domingos. Use Urgencias si es un caso agudo."
    if h < HORARIO_CONSULTA_INICIO or h >= HORARIO_CONSULTA_FIN:
        return (
            f"El horario de consulta es de {HORARIO_CONSULTA_INICIO.strftime('%H:%M')} "
            f"a {HORARIO_CONSULTA_FIN.strftime('%H:%M')}. Fuera de ese rango atienda por Urgencias."
        )
    return ""


def rango_numeros_ok(minimo, maximo, etiqueta="valor") -> str:
    """Vacío si el rango numérico es válido; mensaje si hay negativos o min > max."""
    a, b = minimo, maximo
    if a is not None:
        try:
            a = float(a)
        except (TypeError, ValueError):
            return f"La {etiqueta} mínima no es un número válido."
        if a < 0:
            return f"La {etiqueta} mínima no puede ser negativa."
    if b is not None:
        try:
            b = float(b)
        except (TypeError, ValueError):
            return f"La {etiqueta} máxima no es un número válido."
        if b < 0:
            return f"La {etiqueta} máxima no puede ser negativa."
    if a is not None and b is not None and b < a:
        return f"La {etiqueta} máxima no puede ser menor que la mínima."
    return ""
