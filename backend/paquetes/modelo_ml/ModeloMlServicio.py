"""
ModeloMlServicio — P14 Gestión del modelo de Machine Learning (departamento Datos
e Ingeniería). Reutiliza PrediccionServicio (P6) para entrenar/consultar el modelo
y añade gestión: información del modelo e historial de entrenamientos persistido en
MinIO `diabcare-app/modelos/historial.json`.
"""

import io
import json
from datetime import datetime

from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
from paquetes.prediccion import PrediccionServicio

BUCKET_APP = "diabcare-app"
ARCHIVO_HISTORIAL = "modelos/historial.json"

ALGORITMO = "RandomForestClassifier"
N_ESTIMATORS = 100
SPLIT = "80% entrenamiento / 20% prueba"


def info() -> dict:
    disponible = PrediccionServicio.modelo_disponible()
    metricas = PrediccionServicio.obtener_metricas()
    return {
        "algoritmo": ALGORITMO,
        "n_estimators": N_ESTIMATORS,
        "features": PrediccionServicio.FEATURES,
        "split": SPLIT,
        "disponible": disponible,
        "metricas": None if "error" in metricas else metricas,
    }


def _leer_historial() -> list:
    try:
        c = get_cliente()
        obj = c.get_object(BUCKET_APP, ARCHIVO_HISTORIAL)
        return json.loads(obj.read().decode("utf-8"))
    except Exception:
        return []


def _guardar_historial(historial: list) -> None:
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    contenido = json.dumps(historial, ensure_ascii=False, indent=2).encode("utf-8")
    c.put_object(BUCKET_APP, ARCHIVO_HISTORIAL, io.BytesIO(contenido),
                 length=len(contenido), content_type="application/json")


def historial() -> dict:
    items = _leer_historial()
    items.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return {"total": len(items), "entrenamientos": items}


def reentrenar(usuario: str = "sistema") -> dict:
    resultado = PrediccionServicio.entrenar()
    if "error" in resultado:
        try:
            from paquetes.auditoria.AuditoriaServicio import registrar
            registrar(usuario, "error", "modelo_ml",
                      f"Fallo al reentrenar: {resultado['error']}")
        except Exception:
            pass
        return resultado

    entrada = {
        "fecha": datetime.now().isoformat(),
        "usuario": usuario,
        "accuracy": resultado.get("accuracy"),
        "precision": resultado.get("precision"),
        "recall": resultado.get("recall"),
        "f1": resultado.get("f1"),
        "registros_entrenamiento": resultado.get("registros_entrenamiento"),
        "registros_prueba": resultado.get("registros_prueba"),
    }
    try:
        hist = _leer_historial()
        hist.append(entrada)
        _guardar_historial(hist)
    except Exception as e:
        print(f"[ModeloML] No se pudo guardar historial: {e}")

    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "update", "modelo_ml",
                  f"Modelo reentrenado (accuracy={entrada['accuracy']})")
    except Exception:
        pass
    try:
        from paquetes.notificaciones.NotificacionesServicio import emitir_a_roles
        emitir_a_roles(
            "Modelo ML reentrenado",
            f"El modelo se reentrenó con accuracy {entrada['accuracy']}.",
            "success",
            roles=["analista", "administrador"],
            referencia_tipo="modelo_ml",
        )
    except Exception:
        pass
    return resultado
