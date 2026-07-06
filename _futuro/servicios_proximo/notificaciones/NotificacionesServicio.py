"""
NotificacionesServicio — P10 Notificaciones y alertas (departamento Crecimiento e
Integraciones). Gestiona el centro de alertas del sistema. Persiste en MinIO
`diabcare-app/notificaciones/notificaciones.parquet` (mismo patrón que UsuariosServicio).
"""

import io
import uuid
from datetime import datetime

import pandas as pd

from servicios.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "notificaciones/notificaciones.parquet"
COLUMNAS = ["id", "titulo", "mensaje", "tipo", "leida", "creado_en"]
TIPOS_VALIDOS = {"info", "warning", "error", "success"}


def _extraer() -> pd.DataFrame:
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)


def _cargar(df: pd.DataFrame):
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, ARCHIVO, buf, buf.getbuffer().nbytes)


def crear(titulo: str, mensaje: str, tipo: str = "info") -> dict:
    """Crea una notificación. Resiliente: no lanza excepción al llamador."""
    if tipo not in TIPOS_VALIDOS:
        tipo = "info"
    try:
        df = _extraer()
        nueva = {
            "id": str(uuid.uuid4()),
            "titulo": str(titulo),
            "mensaje": str(mensaje),
            "tipo": tipo,
            "leida": False,
            "creado_en": datetime.now().isoformat(),
        }
        _cargar(pd.concat([df, pd.DataFrame([nueva])], ignore_index=True))
        return {"mensaje": "Notificación creada", "id": nueva["id"]}
    except Exception as e:
        print(f"[Notificaciones] No se pudo crear: {e}")
        return {"error": str(e)}


def listar(tipo: str = None) -> list:
    df = _extraer()
    if df.empty:
        return []
    if tipo:
        df = df[df["tipo"] == tipo]
    df = df.sort_values("creado_en", ascending=False)
    return df.fillna("").to_dict(orient="records")


def marcar_todas_leidas() -> dict:
    df = _extraer()
    if df.empty:
        return {"mensaje": "Sin notificaciones", "actualizadas": 0}
    pendientes = int((~df["leida"].astype(bool)).sum())
    df["leida"] = True
    _cargar(df)
    return {"mensaje": "Notificaciones marcadas como leídas", "actualizadas": pendientes}


def _existe_alerta_reciente(titulo: str, horas: int = 24) -> bool:
    df = _extraer()
    if df.empty:
        return False
    from datetime import timedelta
    limite = datetime.now() - timedelta(hours=horas)
    for _, row in df.iterrows():
        if str(row.get("titulo", "")) == titulo:
            try:
                creado = datetime.fromisoformat(str(row.get("creado_en", "")))
                if creado >= limite:
                    return True
            except Exception:
                pass
    return False


def evaluar_alertas_clinicas() -> dict:
    """RN-O-005: alerta si HbA1c promedio > 7.5."""
    try:
        from servicios.registros_clinicos import RegistrosClinicosServicio
        stats = RegistrosClinicosServicio.estadisticas()
    except Exception:
        return {"evaluado": False}

    total = int(stats.get("total") or 0)
    if total == 0:
        return {"evaluado": True, "alertas": 0}

    con = int(stats.get("con_diabetes") or 0)
    sin = int(stats.get("sin_diabetes") or 0)
    prom = stats.get("promedios", {}).get("hba1c", {})
    hba_con = float(prom.get("con") or 0)
    hba_sin = float(prom.get("sin") or 0)
    avg = (hba_con * con + hba_sin * sin) / total if total else 0

    creadas = 0
    titulo_hba = "Alerta HbA1c elevada"
    if avg > 7.5 and not _existe_alerta_reciente(titulo_hba):
        crear(
            titulo_hba,
            f"HbA1c promedio {avg:.1f}% supera el umbral clínico de 7.5% (RN-O-005).",
            "warning",
        )
        creadas += 1

    prev = (con / total * 100) if total else 0
    titulo_prev = "Prevalencia diabetes alta"
    if prev > 50 and not _existe_alerta_reciente(titulo_prev):
        crear(
            titulo_prev,
            f"Prevalencia de diabetes {prev:.1f}% — revise cohortes de alto riesgo.",
            "warning",
        )
        creadas += 1

    return {"evaluado": True, "alertas": creadas, "hba1c_promedio": round(avg, 2)}


def evaluar_alertas_churn() -> dict:
    """CU-O16 / OO4.2.1: señales de abandono o baja actividad del tenant."""
    from datetime import timedelta
    creadas = 0
    try:
        from servicios.auditoria.AuditoriaServicio import _extraer as extraer_auditoria
        df = extraer_auditoria()
    except Exception:
        df = pd.DataFrame()

    if not df.empty and "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        ahora = datetime.now()
        reciente = df[df["fecha"] >= ahora - timedelta(days=7)]
        anterior = df[(df["fecha"] >= ahora - timedelta(days=14)) & (df["fecha"] < ahora - timedelta(days=7))]
        n_rec = len(reciente)
        n_ant = len(anterior)
        if n_ant >= 5 and n_rec < n_ant * 0.4:
            titulo = "Alerta churn: actividad en caída"
            if not _existe_alerta_reciente(titulo):
                crear(
                    titulo,
                    f"Eventos últimos 7 días ({n_rec}) < 40% del periodo anterior ({n_ant}). OO4.2.1",
                    "error",
                )
                creadas += 1

    try:
        from servicios.dataset.DatasetDwhServicio import resumen_dwh
        dwh = resumen_dwh()
        if not dwh.get("materializado"):
            titulo = "Alerta churn: DWH sin materializar"
            if not _existe_alerta_reciente(titulo, horas=72):
                crear(titulo, "Sin datos DWH recientes — riesgo de abandono analítico.", "warning")
                creadas += 1
    except Exception:
        pass

    try:
        from servicios.integraciones.IntegracionesServicio import _leer_parquet, ARCHIVO_PAGOS, COL_PAGOS
        pagos = _leer_parquet(ARCHIVO_PAGOS, COL_PAGOS)
        if not pagos.empty:
            pendientes = int((pagos["estado"] == "pendiente").sum())
            if pendientes >= 3:
                titulo = "Alerta churn: pagos pendientes"
                if not _existe_alerta_reciente(titulo):
                    crear(
                        titulo,
                        f"{pendientes} suscripciones con pago pendiente (CU-O12/OO1.2.1).",
                        "warning",
                    )
                    creadas += 1
    except Exception:
        pass

    return {"evaluado": True, "alertas_churn": creadas, "cu_o": "CU-O16", "oo": "OO4.2.1"}


def evaluar_todas() -> dict:
    clin = evaluar_alertas_clinicas()
    churn = evaluar_alertas_churn()
    return {
        "clinicas": clin,
        "churn": churn,
        "total_alertas": int(clin.get("alertas", 0)) + int(churn.get("alertas_churn", 0)),
    }
