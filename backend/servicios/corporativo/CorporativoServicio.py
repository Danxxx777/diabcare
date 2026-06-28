"""
CorporativoServicio — P9 Información corporativa (departamento Inteligencia de
Negocio). Expone la información institucional (misión, visión, objetivos) derivada
del TA06 y la especificación general. Editable por administrador; se persiste como
JSON en MinIO `diabcare-app/configuracion/corporativo.json`.
"""

import io
import json

from servicios.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "configuracion/corporativo.json"

DEFAULTS = {
    "nombre": "DiabCare Analytics",
    "descripcion": ("Plataforma SaaS de análisis clínico de datos de diabetes "
                    "hospitalaria, con flujo ELT y modelos de Machine Learning."),
    "mision": ("Facilitar el análisis de datos clínicos de diabetes con una "
               "plataforma web, ELT y Machine Learning."),
    "vision": "Ser plataforma de referencia escalando globalmente como SaaS.",
    "objetivos_estrategicos": [
        "Expansión internacional mediante growth digital, APIs, nube e "
        "inteligencia de negocio (BI).",
    ],
    "objetivos_tacticos": [
        "Consolidar el flujo ELT y la calidad del dato clínico.",
        "Mantener el modelo de predicción con exactitud objetivo >= 96%.",
    ],
    "objetivos_operativos": [
        "Operar registros clínicos, predicción, análisis y reportes del día a día.",
        "Garantizar seguridad por roles y trazabilidad de auditoría.",
    ],
}


def obtener() -> dict:
    try:
        c = get_cliente()
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        guardado = json.loads(obj.read().decode("utf-8"))
    except Exception:
        guardado = {}
    return {**DEFAULTS, **guardado}


def actualizar(datos: dict, usuario: str = "sistema") -> dict:
    actual = obtener()
    nuevo = {**actual, **{k: v for k, v in (datos or {}).items() if k in DEFAULTS}}
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        contenido = json.dumps(nuevo, ensure_ascii=False, indent=2).encode("utf-8")
        c.put_object(BUCKET_APP, ARCHIVO, io.BytesIO(contenido), length=len(contenido),
                     content_type="application/json")
    except Exception as e:
        return {"error": f"No se pudo guardar la información corporativa: {e}"}

    try:
        from servicios.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "update", "corporativo", "Información corporativa actualizada")
    except Exception:
        pass
    return {"mensaje": "Información corporativa actualizada", "corporativo": nuevo}
