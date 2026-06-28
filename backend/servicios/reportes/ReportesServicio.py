"""
ReportesServicio — P7 Reportes PDF (nivel operativo, departamento Clínico/Análisis).

Genera reportes clínicos descargables en PDF con:
  1. Estadísticas del dataset (reutiliza RegistrosClinicosServicio.estadisticas()).
  2. Métricas del modelo ML (reutiliza PrediccionServicio.obtener_metricas()).
  3. Resumen de registros filtrados (reutiliza la misma extracción y filtros que
     RegistrosClinicosServicio.buscar(), pero agregando sobre el subconjunto completo).

Persistencia: MinIO, bucket 'diabcare-app', prefijo 'reportes/'.
Auditoría: se registran los eventos de generación y descarga vía logging estándar
(el módulo de auditoría P11 aún no está implementado; aquí no se inventa dependencia).
"""

import io
import logging
from datetime import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from servicios.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
PREFIJO_REPORTES = "reportes/"

logger = logging.getLogger("diabcare.reportes")


# ---------------------------------------------------------------------------
# Utilidades MinIO
# ---------------------------------------------------------------------------
def _asegurar_bucket(cliente):
    if not cliente.bucket_exists(BUCKET_APP):
        cliente.make_bucket(BUCKET_APP)


def _subir_pdf(nombre: str, contenido: bytes) -> dict:
    cliente = get_cliente()
    _asegurar_bucket(cliente)
    objeto = f"{PREFIJO_REPORTES}{nombre}"
    cliente.put_object(
        BUCKET_APP,
        objeto,
        io.BytesIO(contenido),
        length=len(contenido),
        content_type="application/pdf",
    )
    return {
        "nombre": nombre,
        "ruta": f"{BUCKET_APP}/{objeto}",
        "tamano_mb": round(len(contenido) / (1024 * 1024), 4),
    }


def listar_reportes() -> list:
    """Lista los reportes previos almacenados en MinIO (nombre, fecha, tamaño)."""
    try:
        cliente = get_cliente()
        if not cliente.bucket_exists(BUCKET_APP):
            return []
        objetos = cliente.list_objects(BUCKET_APP, prefix=PREFIJO_REPORTES, recursive=True)
        reportes = []
        for obj in objetos:
            if not obj.object_name.endswith(".pdf"):
                continue
            reportes.append({
                "nombre": obj.object_name.replace(PREFIJO_REPORTES, "", 1),
                "fecha": obj.last_modified.isoformat() if obj.last_modified else None,
                "tamano_mb": round((obj.size or 0) / (1024 * 1024), 4),
            })
        reportes.sort(key=lambda r: r["fecha"] or "", reverse=True)
        return reportes
    except Exception as e:
        logger.warning("No se pudieron listar reportes: %s", e)
        return []


def descargar_reporte(nombre: str):
    """Devuelve el contenido binario del PDF, o None si no existe."""
    try:
        cliente = get_cliente()
        objeto = f"{PREFIJO_REPORTES}{nombre}"
        respuesta = cliente.get_object(BUCKET_APP, objeto)
        contenido = respuesta.read()
        logger.info("AUDIT reporte_descargado nombre=%s", nombre)
        try:
            from servicios.auditoria.AuditoriaServicio import registrar
            registrar("sistema", "info", "reportes", f"Reporte descargado: {nombre}")
        except Exception:
            pass
        return contenido
    except Exception as e:
        logger.warning("Reporte no encontrado '%s': %s", nombre, e)
        return None


# ---------------------------------------------------------------------------
# Fuentes de datos (reutilización de servicios existentes)
# ---------------------------------------------------------------------------
def _estadisticas_dataset() -> dict:
    try:
        from servicios.registros_clinicos.RegistrosClinicosServicio import estadisticas
        return estadisticas() or {"total": 0}
    except Exception as e:
        logger.warning("Estadísticas no disponibles: %s", e)
        return {"total": 0}


def _metricas_modelo() -> dict:
    try:
        from servicios.prediccion.PrediccionServicio import obtener_metricas
        return obtener_metricas() or {"error": "no disponible"}
    except Exception as e:
        logger.warning("Métricas del modelo no disponibles: %s", e)
        return {"error": "no disponible"}


def _resumen_filtrado(filtros: dict) -> dict:
    """
    Calcula agregados sobre el subconjunto filtrado completo.
    Reaplica los mismos filtros que RegistrosClinicosServicio.buscar() pero sobre
    todo el DataFrame para que los conteos coincidan con la vista de registros.
    Solo devuelve agregados — nunca filas ni encounter_id (RNF-O-P07-002).
    """
    try:
        from servicios.registros_clinicos.RegistrosClinicosServicio import _extraer
        df = _extraer()
        if df.empty:
            return {"total": 0}

        if filtros.get("diabetes") is not None:
            df = df[df["diabetes"] == filtros["diabetes"]]
        if filtros.get("gender"):
            df = df[df["gender"] == filtros["gender"]]
        if filtros.get("location"):
            df = df[df["location"].str.contains(filtros["location"], case=False, na=False)]
        if filtros.get("age_min") is not None:
            df = df[df["age"] >= filtros["age_min"]]
        if filtros.get("age_max") is not None:
            df = df[df["age"] <= filtros["age_max"]]

        total = int(len(df))
        if total == 0:
            return {"total": 0}

        return {
            "total": total,
            "con_diabetes": int((df["diabetes"] == 1).sum()),
            "sin_diabetes": int((df["diabetes"] == 0).sum()),
            "genero": {str(k): int(v) for k, v in df["gender"].value_counts().to_dict().items()},
            "promedios": {
                "bmi": round(float(df["bmi"].mean()), 2),
                "hba1c": round(float(df["hbA1c_level"].mean()), 2),
                "glucosa": round(float(df["blood_glucose_level"].mean()), 1),
            },
        }
    except Exception as e:
        logger.warning("Resumen filtrado no disponible: %s", e)
        return {"total": 0}


# ---------------------------------------------------------------------------
# Construcción del PDF
# ---------------------------------------------------------------------------
def _txt(valor) -> str:
    """Sanitiza el texto al rango latin-1 que soportan las fuentes core de fpdf2."""
    return str(valor).encode("latin-1", "replace").decode("latin-1")


class _ReportePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(20, 60, 110)
        self.cell(0, 10, _txt("DiabCare Analytics — Reporte Clínico"))
        self.ln(12)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, _txt(f"Página {self.page_no()}"), align="C")


def _titulo(pdf, texto):
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(230, 238, 248)
    pdf.cell(0, 8, _txt(texto), fill=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 11)


def _linea(pdf, etiqueta, valor):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(60, 6, _txt(etiqueta), new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, _txt(valor), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _seccion_dataset(pdf, est):
    _titulo(pdf, "1. Estadísticas del dataset")
    total = est.get("total", 0)
    if not total:
        pdf.multi_cell(0, 6, _txt("Estadísticas del dataset no disponibles."))
        return
    con = est.get("con_diabetes", 0)
    pct = round(con / total * 100, 2) if total else 0
    _linea(pdf, "Total de registros:", f"{total}")
    _linea(pdf, "Con diabetes:", f"{con} ({pct}%)")
    _linea(pdf, "Sin diabetes:", f"{est.get('sin_diabetes', 0)}")
    genero = est.get("genero", {})
    if genero:
        _linea(pdf, "Distribución por género:",
               ", ".join(f"{k}: {v}" for k, v in genero.items()))
    prom = est.get("promedios", {})
    if prom:
        bmi = prom.get("bmi", {})
        hba = prom.get("hba1c", {})
        glu = prom.get("glucosa", {})
        _linea(pdf, "BMI (con/sin):", f"{bmi.get('con', '-')} / {bmi.get('sin', '-')}")
        _linea(pdf, "HbA1c (con/sin):", f"{hba.get('con', '-')} / {hba.get('sin', '-')}")
        _linea(pdf, "Glucosa (con/sin):", f"{glu.get('con', '-')} / {glu.get('sin', '-')}")


def _seccion_modelo(pdf, met):
    _titulo(pdf, "2. Métricas del modelo de Machine Learning")
    if not met or "error" in met:
        pdf.multi_cell(0, 6, _txt("Métricas del modelo no disponibles "
                                  "(el modelo aún no ha sido entrenado)."))
        return
    _linea(pdf, "Exactitud (accuracy):", f"{met.get('accuracy', '-')}")
    _linea(pdf, "Precisión (precision):", f"{met.get('precision', '-')}")
    _linea(pdf, "Sensibilidad (recall):", f"{met.get('recall', '-')}")
    _linea(pdf, "F1-score:", f"{met.get('f1', '-')}")
    _linea(pdf, "Registros entrenamiento:", f"{met.get('registros_entrenamiento', '-')}")
    _linea(pdf, "Registros prueba:", f"{met.get('registros_prueba', '-')}")


def _seccion_filtrado(pdf, filtros, resumen):
    _titulo(pdf, "3. Resumen de registros filtrados")
    if filtros:
        descripcion = ", ".join(f"{k}={v}" for k, v in filtros.items())
        _linea(pdf, "Filtros aplicados:", descripcion)
    else:
        _linea(pdf, "Filtros aplicados:", "ninguno (todo el dataset)")
    total = resumen.get("total", 0)
    if not total:
        pdf.multi_cell(0, 6, _txt("Sin registros para los filtros aplicados."))
        return
    _linea(pdf, "Registros coincidentes:", f"{total}")
    _linea(pdf, "Con diabetes:", f"{resumen.get('con_diabetes', 0)}")
    _linea(pdf, "Sin diabetes:", f"{resumen.get('sin_diabetes', 0)}")
    genero = resumen.get("genero", {})
    if genero:
        _linea(pdf, "Distribución por género:",
               ", ".join(f"{k}: {v}" for k, v in genero.items()))
    prom = resumen.get("promedios", {})
    if prom:
        _linea(pdf, "Promedios (BMI / HbA1c / Glucosa):",
               f"{prom.get('bmi', '-')} / {prom.get('hba1c', '-')} / {prom.get('glucosa', '-')}")


def generar_pdf(filtros: dict, usuario: str) -> bytes:
    """Construye el reporte PDF completo y devuelve su contenido binario."""
    filtros = filtros or {}
    est = _estadisticas_dataset()
    met = _metricas_modelo()
    resumen = _resumen_filtrado(filtros)

    pdf = _ReportePDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, _txt(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    pdf.ln(6)
    pdf.cell(0, 6, _txt(f"Usuario: {usuario}"))
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)

    _seccion_dataset(pdf, est)
    _seccion_modelo(pdf, met)
    _seccion_filtrado(pdf, filtros, resumen)

    salida = pdf.output()
    return bytes(salida)


def generar_y_subir(filtros: dict, usuario: str) -> dict:
    """Genera el PDF, lo persiste en MinIO y devuelve los metadatos del reporte."""
    contenido = generar_pdf(filtros, usuario)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"reporte_{timestamp}.pdf"
    metadatos = _subir_pdf(nombre, contenido)
    metadatos["fecha"] = datetime.now().isoformat()
    logger.info("AUDIT reporte_generado nombre=%s usuario=%s filtros=%s",
                nombre, usuario, filtros)
    try:
        from servicios.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "create", "reportes", f"Reporte generado: {nombre}")
    except Exception:
        pass
    try:
        from servicios.notificaciones.NotificacionesServicio import crear as _notif
        _notif("Reporte generado", f"Se generó el reporte {nombre}.", "success")
    except Exception:
        pass
    return metadatos
