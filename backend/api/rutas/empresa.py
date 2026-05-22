"""
empresa.py — Endpoint de información corporativa de DiabCare Analytics
"""

from fastapi import APIRouter

enrutador = APIRouter()


@enrutador.get("/api/empresa")
def obtener_empresa():
    """Retorna la información corporativa de DiabCare Analytics."""
    return {
        "nombre": "DiabCare Analytics",
        "slogan": "Datos que salvan vidas",
        "mision": (
            "Proveer soluciones tecnológicas de análisis de datos clínicos que permitan "
            "a hospitales y redes de salud optimizar la atención de pacientes diabéticos, "
            "reduciendo tasas de readmisión y mejorando la toma de decisiones médicas "
            "mediante el uso inteligente de la información."
        ),
        "vision": (
            "Ser la plataforma líder en Latinoamérica para la gestión analítica de datos "
            "clínicos de diabetes hospitalaria para 2030, reconocida por la precisión de "
            "sus modelos predictivos y la calidad de sus herramientas de soporte a "
            "decisiones médicas."
        ),
        "objetivos_estrategicos": [
            "Consolidar una plataforma centralizada de datos clínicos interoperable con los principales sistemas hospitalarios.",
            "Desarrollar modelos predictivos de readmisión hospitalaria con precisión superior al 80%.",
            "Expandir la cobertura a 50 hospitales en la región en un plazo de 3 años.",
        ],
        "objetivos_tacticos": [
            "Implementar pipelines automatizados de ingesta y limpieza de datos clínicos cada semestre.",
            "Capacitar al personal médico y administrativo en el uso de los dashboards de analítica.",
            "Establecer acuerdos de integración de datos con al menos 10 hospitales por año.",
        ],
        "objetivos_operacionales": [
            "Ejecutar la carga del dataset clínico diariamente de forma automatizada sin intervención manual.",
            "Garantizar disponibilidad del sistema web al 99.5% mensual.",
            "Generar reportes automáticos de readmisión cada 24 horas para el equipo médico.",
        ],
    }
