"""
ReportesServicio — reportes clínicos agregados en PDF.

Incluye estadísticas del dataset, métricas del modelo ML y resumen filtrado.
Solo datos agregados — sin identificadores de pacientes.
"""

from __future__ import annotations

import io
import json
import logging
import os
import secrets
import tempfile
from datetime import datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from paquetes.dataset.DatasetTraducciones import aliases_genero, normalizar_genero
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
PREFIJO_REPORTES = "reportes/"
ROOT_DIR = Path(__file__).resolve().parents[3]
LOGO_PATH = ROOT_DIR / "frontend" / "estaticos" / "img" / "logo-icon.png"

# Colores marca DiabCare (RGB)
COLOR_PRIMARIO = (14, 116, 144)      # cyan clínico
COLOR_ACENTO = (34, 211, 238)
COLOR_TEXTO = (30, 41, 59)
COLOR_MUTED = (100, 116, 139)
COLOR_FONDO_SEC = (236, 254, 255)

logger = logging.getLogger("diabcare.reportes")


# ---------------------------------------------------------------------------
# Utilidades MinIO
# ---------------------------------------------------------------------------
def _asegurar_bucket(cliente):
    if not cliente.bucket_exists(BUCKET_APP):
        cliente.make_bucket(BUCKET_APP)


def _subir_pdf(nombre: str, contenido: bytes, codigo: str = "") -> dict:
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
    if codigo:
        meta_obj = f"{PREFIJO_REPORTES}{nombre}.meta.json"
        body = json.dumps({"codigo_verificacion": codigo}, ensure_ascii=False).encode("utf-8")
        cliente.put_object(BUCKET_APP, meta_obj, io.BytesIO(body), len(body), content_type="application/json")
    return {
        "nombre": nombre,
        "ruta": f"{BUCKET_APP}/{objeto}",
        "tamano_mb": round(len(contenido) / (1024 * 1024), 4),
    }


def _leer_meta_reporte(cliente, nombre: str) -> dict:
    try:
        obj = cliente.get_object(BUCKET_APP, f"{PREFIJO_REPORTES}{nombre}.meta.json")
        return json.loads(obj.read())
    except Exception:
        return {}


def listar_reportes() -> list:
    try:
        cliente = get_cliente()
        if not cliente.bucket_exists(BUCKET_APP):
            return []
        objetos = cliente.list_objects(BUCKET_APP, prefix=PREFIJO_REPORTES, recursive=True)
        reportes = []
        for obj in objetos:
            if not obj.object_name.endswith(".pdf"):
                continue
            nombre = obj.object_name.replace(PREFIJO_REPORTES, "", 1)
            meta = _leer_meta_reporte(cliente, nombre)
            reportes.append({
                "nombre": nombre,
                "fecha": obj.last_modified.isoformat() if obj.last_modified else None,
                "tamano_mb": round((obj.size or 0) / (1024 * 1024), 4),
                "codigo_verificacion": meta.get("codigo_verificacion"),
            })
        reportes.sort(key=lambda r: r["fecha"] or "", reverse=True)
        return reportes
    except Exception as e:
        logger.warning("No se pudieron listar reportes: %s", e)
        return []


def descargar_reporte(nombre: str):
    try:
        cliente = get_cliente()
        objeto = f"{PREFIJO_REPORTES}{nombre}"
        respuesta = cliente.get_object(BUCKET_APP, objeto)
        contenido = respuesta.read()
        logger.info("AUDIT reporte_descargado nombre=%s", nombre)
        try:
            from paquetes.auditoria.AuditoriaServicio import registrar
            registrar("sistema", "info", "reportes", f"Reporte descargado: {nombre}")
        except Exception:
            pass
        return contenido
    except Exception as e:
        logger.warning("Reporte no encontrado '%s': %s", nombre, e)
        return None


# ---------------------------------------------------------------------------
# Fuentes de datos
# ---------------------------------------------------------------------------
def _estadisticas_dataset() -> dict:
    try:
        from paquetes.registros_clinicos.RegistrosClinicosServicio import estadisticas
        return estadisticas() or {"total": 0}
    except Exception as e:
        logger.warning("Estadísticas no disponibles: %s", e)
        return {"total": 0}


def _metricas_modelo() -> dict:
    try:
        from paquetes.prediccion.PrediccionServicio import obtener_metricas
        return obtener_metricas() or {"error": "no disponible"}
    except Exception as e:
        logger.warning("Métricas del modelo no disponibles: %s", e)
        return {"error": "no disponible"}


def _resumen_filtrado(filtros: dict) -> dict:
    try:
        from paquetes.registros_clinicos.RegistrosClinicosServicio import _extraer
        df = _extraer()
        if df.empty:
            return {"total": 0}

        if filtros.get("diabetes") is not None:
            df = df[df["diabetes"] == filtros["diabetes"]]
        if filtros.get("gender"):
            vals = aliases_genero(filtros["gender"])
            df = df[df["gender"].isin(vals)]
        if filtros.get("location"):
            df = df[df["location"].str.contains(filtros["location"], case=False, na=False)]
        if filtros.get("year") is not None and "year" in df.columns:
            df = df[df["year"] == filtros["year"]]
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
            "genero": {normalizar_genero(k): int(v) for k, v in df["gender"].value_counts().to_dict().items()},
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
# PDF — utilidades
# ---------------------------------------------------------------------------
def _txt(valor) -> str:
    return str(valor).encode("latin-1", "replace").decode("latin-1")


def _fmt_num(n) -> str:
    try:
        return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(n)


def _describir_filtros(filtros: dict) -> str:
    if not filtros:
        return "Sin filtros — incluye todo el dataset clínico disponible."
    partes = []
    if filtros.get("diabetes") is not None:
        partes.append("Con diabetes" if filtros["diabetes"] == 1 else "Sin diabetes")
    if filtros.get("gender"):
        partes.append(f"Género: {filtros['gender']}")
    if filtros.get("location"):
        partes.append(f"Ubicación contiene «{filtros['location']}»")
    if filtros.get("year") is not None:
        partes.append(f"Año {filtros['year']}")
    if filtros.get("age_min") is not None:
        partes.append(f"Edad mínima {filtros['age_min']} años")
    if filtros.get("age_max") is not None:
        partes.append(f"Edad máxima {filtros['age_max']} años")
    return " · ".join(partes) if partes else "Sin filtros adicionales."


def _payload_qr(codigo: str, nombre: str, generado: str) -> str:
    """Payload estructurado para verificación futura (portal / app móvil)."""
    return json.dumps({
        "v": 1,
        "tipo": "reporte_clinico",
        "app": "DiabCare",
        "codigo": codigo,
        "archivo": nombre,
        "generado": generado,
    }, ensure_ascii=False, separators=(",", ":"))


def _generar_qr_png(contenido: str) -> str | None:
    try:
        import qrcode
        qr = qrcode.QRCode(version=2, box_size=4, border=1)
        qr.add_data(contenido)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        img.save(path)
        return path
    except Exception as e:
        logger.warning("No se pudo generar QR: %s", e)
        return None


class _ReportePDF(FPDF):
    def __init__(self, meta: dict, qr_path: str | None = None):
        super().__init__()
        self.meta = meta
        self.qr_path = qr_path

    def header(self):
        y0 = self.get_y()
        if LOGO_PATH.is_file():
            self.image(str(LOGO_PATH), x=self.l_margin, y=10, h=14)
            tx = self.l_margin + 18
        else:
            tx = self.l_margin
        self.set_xy(tx, 10)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*COLOR_PRIMARIO)
        self.cell(0, 6, _txt("DiabCare Analytics"))
        self.ln(5)
        self.set_x(tx)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*COLOR_MUTED)
        self.cell(0, 5, _txt("Plataforma de analítica clínica en diabetes"))
        self.set_y(max(y0, 28))
        self.set_draw_color(*COLOR_ACENTO)
        self.set_line_width(0.4)
        self.line(self.l_margin, 26, self.w - self.r_margin, 26)
        self.ln(8)
        self.set_text_color(*COLOR_TEXTO)

    def footer(self):
        self.set_y(-22)
        qr_w = 16
        if self.qr_path and os.path.isfile(self.qr_path):
            self.image(self.qr_path, x=self.l_margin, y=self.get_y(), w=qr_w)
            self.set_xy(self.l_margin + qr_w + 2, self.get_y() + 1)
            self.set_font("Helvetica", "", 6.5)
            self.set_text_color(*COLOR_MUTED)
            self.multi_cell(42, 3.2, _txt(
                f"Código {self.meta.get('codigo', '—')}\n"
                "Verificación documental\n(próximamente: portal web)"
            ))
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*COLOR_MUTED)
        self.set_xy(0, -12)
        self.cell(0, 8, _txt(f"Página {self.page_no()} · Documento confidencial — uso clínico interno"), align="C")


def _bloque_titulo(pdf: FPDF, numero: str, titulo: str, subtitulo: str = ""):
    pdf.ln(4)
    pdf.set_fill_color(*COLOR_FONDO_SEC)
    pdf.set_draw_color(*COLOR_ACENTO)
    pdf.set_line_width(0.2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*COLOR_PRIMARIO)
    pdf.cell(0, 8, _txt(f"  {numero}. {titulo}"), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if subtitulo:
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*COLOR_MUTED)
        pdf.multi_cell(0, 4.5, _txt(subtitulo))
    pdf.ln(4)
    pdf.set_text_color(*COLOR_TEXTO)


def _fila_metrica(pdf: FPDF, etiqueta: str, valor: str, ayuda: str = ""):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(52, 6, _txt(etiqueta), new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _txt(valor), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if ayuda:
        pdf.set_x(pdf.l_margin + 4)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*COLOR_MUTED)
        pdf.multi_cell(0, 4, _txt(ayuda))
        pdf.set_text_color(*COLOR_TEXTO)
        pdf.ln(1)


def _portada(pdf: FPDF, meta: dict, filtros: dict):
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*COLOR_TEXTO)
    pdf.cell(0, 10, _txt("Reporte clínico agregado"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.multi_cell(0, 5, _txt(
        "Resumen estadístico para equipos clínicos y de gestión. "
        "Los datos están anonimizados y agregados; no incluye nombres ni documentos de pacientes."
    ))
    pdf.ln(6)

    x0, y0 = pdf.get_x(), pdf.get_y()
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(x0, y0, pdf.w - pdf.l_margin - pdf.r_margin, 34, style="DF")
    pdf.set_xy(x0 + 6, y0 + 5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*COLOR_PRIMARIO)
    pdf.cell(0, 5, _txt("Datos del documento"))
    pdf.ln(6)
    filas = [
        ("Código de verificación:", meta.get("codigo", "—")),
        ("Generado:", meta.get("fecha_hora", "—")),
        ("Responsable:", meta.get("usuario", "—")),
        ("Alcance:", _describir_filtros(filtros)),
    ]
    for etq, val in filas:
        pdf.set_x(x0 + 6)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*COLOR_TEXTO)
        pdf.cell(38, 5, _txt(etq), new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(pdf.w - pdf.r_margin - x0 - 44, 5, _txt(val))
    pdf.set_y(y0 + 38)


def _resumen_ejecutivo(pdf: FPDF, est: dict, met: dict, resumen: dict):
    _bloque_titulo(pdf, "", "Resumen ejecutivo",
                   "Lectura rápida de los hallazgos principales del reporte.")
    total_ds = est.get("total", 0)
    total_f = resumen.get("total", 0)
    lineas = []
    if total_ds:
        pct = round(est.get("con_diabetes", 0) / total_ds * 100, 1) if total_ds else 0
        lineas.append(f"• El dataset contiene {_fmt_num(total_ds)} registros clínicos; {pct}% presentan diagnóstico de diabetes.")
    if total_f:
        pct_f = round(resumen.get("con_diabetes", 0) / total_f * 100, 1) if total_f else 0
        lineas.append(f"• Con los filtros aplicados se analizaron {_fmt_num(total_f)} registros ({pct_f}% con diabetes).")
    if met and "error" not in met:
        acc = met.get("accuracy", "—")
        lineas.append(f"• El modelo predictivo activo alcanza {acc} de exactitud en prueba.")
    else:
        lineas.append("• El modelo predictivo aún no está entrenado o no hay métricas disponibles.")
    lineas.append("• Este documento es válido como respaldo analítico interno; no sustituye un informe médico individual.")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5.5, _txt("\n".join(lineas)))
    pdf.ln(4)


def _seccion_dataset(pdf: FPDF, est: dict):
    _bloque_titulo(pdf, "1", "Panorama del dataset clínico",
                   "Estadísticas globales de todos los registros disponibles en la plataforma.")
    total = est.get("total", 0)
    if not total:
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _txt("No hay estadísticas disponibles en este momento."))
        return
    con = est.get("con_diabetes", 0)
    sin = est.get("sin_diabetes", 0)
    pct = round(con / total * 100, 1) if total else 0
    _fila_metrica(pdf, "Total registros", _fmt_num(total),
                  "Consultas clínicas anonimizadas almacenadas en el sistema.")
    _fila_metrica(pdf, "Con diabetes", f"{_fmt_num(con)} ({pct}%)",
                  "Pacientes con diagnóstico positivo de diabetes mellitus.")
    _fila_metrica(pdf, "Sin diabetes", _fmt_num(sin))
    genero = est.get("genero", {})
    if genero:
        txt = "  ·  ".join(f"{k}: {_fmt_num(v)}" for k, v in genero.items())
        _fila_metrica(pdf, "Por género", txt)
    prom = est.get("promedios", {})
    if prom:
        bmi = prom.get("bmi", {})
        hba = prom.get("hba1c", {})
        glu = prom.get("glucosa", {})
        _fila_metrica(pdf, "BMI promedio", f"Con DM: {bmi.get('con', '—')}  ·  Sin DM: {bmi.get('sin', '—')}",
                      "Índice de masa corporal (kg/m²). Normal: 18.5–24.9.")
        _fila_metrica(pdf, "HbA1c promedio", f"Con DM: {hba.get('con', '—')} %  ·  Sin DM: {hba.get('sin', '—')} %",
                      "Hemoglobina glicosilada. Control óptimo: < 7%.")
        _fila_metrica(pdf, "Glucosa promedio", f"Con DM: {glu.get('con', '—')}  ·  Sin DM: {glu.get('sin', '—')} mg/dL",
                      "Nivel de glucosa en sangre. Ayunas normal: 70–100 mg/dL.")


def _seccion_modelo(pdf: FPDF, met: dict):
    _bloque_titulo(pdf, "2", "Modelo predictivo de diabetes",
                   "Rendimiento del algoritmo de machine learning entrenado con los datos clínicos.")
    if not met or "error" in met:
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _txt(
            "No hay métricas disponibles. Entrene el modelo en el módulo «Modelo ML» "
            "para incluir esta sección en futuros reportes."
        ))
        return
    _fila_metrica(pdf, "Exactitud (accuracy)", str(met.get("accuracy", "—")),
                  "Proporción de predicciones correctas sobre el total.")
    _fila_metrica(pdf, "Precisión", str(met.get("precision", "—")),
                  "De los casos predichos como positivos, cuántos realmente lo son.")
    _fila_metrica(pdf, "Sensibilidad (recall)", str(met.get("recall", "—")),
                  "De los casos reales positivos, cuántos detecta el modelo.")
    _fila_metrica(pdf, "F1-score", str(met.get("f1", "—")),
                  "Media armónica entre precisión y sensibilidad.")
    _fila_metrica(pdf, "Datos entrenamiento", _fmt_num(met.get("registros_entrenamiento", "—")))
    _fila_metrica(pdf, "Datos prueba", _fmt_num(met.get("registros_prueba", "—")))


def _seccion_filtrado(pdf: FPDF, filtros: dict, resumen: dict):
    _bloque_titulo(pdf, "3", "Análisis del subconjunto seleccionado",
                   "Resultados aplicando los filtros definidos al generar este reporte.")
    _fila_metrica(pdf, "Criterios", _describir_filtros(filtros))
    total = resumen.get("total", 0)
    if not total:
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _txt("No hay registros que coincidan con los filtros indicados."))
        return
    con = resumen.get("con_diabetes", 0)
    pct = round(con / total * 100, 1) if total else 0
    _fila_metrica(pdf, "Registros analizados", _fmt_num(total))
    _fila_metrica(pdf, "Con diabetes", f"{_fmt_num(con)} ({pct}%)")
    _fila_metrica(pdf, "Sin diabetes", _fmt_num(resumen.get("sin_diabetes", 0)))
    genero = resumen.get("genero", {})
    if genero:
        _fila_metrica(pdf, "Distribución por género",
                      "  ·  ".join(f"{k}: {_fmt_num(v)}" for k, v in genero.items()))
    prom = resumen.get("promedios", {})
    if prom:
        _fila_metrica(pdf, "Promedios del subconjunto",
                      f"BMI {prom.get('bmi', '—')}  ·  HbA1c {prom.get('hba1c', '—')} %  ·  "
                      f"Glucosa {prom.get('glucosa', '—')} mg/dL")


def _seccion_glosario_qr(pdf: FPDF):
    _bloque_titulo(pdf, "4", "Glosario y verificación del documento")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 4.5, _txt(
        "BMI — Índice de masa corporal.  ·  HbA1c — Control glucémico a 2–3 meses.  ·  "
        "Glucosa — Nivel en sangre (mg/dL).  ·  DM — Diabetes mellitus.\n\n"
        "El código QR impreso en el pie de página permite verificar la autenticidad de este reporte. "
        "En una próxima versión podrá escanearse para abrir el portal de validación, descargar una copia "
        "certificada o vincular el documento a auditoría institucional."
    ))


def generar_pdf(filtros: dict, usuario: str, codigo: str, nombre_archivo: str) -> bytes:
    filtros = filtros or {}
    est = _estadisticas_dataset()
    met = _metricas_modelo()
    resumen = _resumen_filtrado(filtros)
    ahora = datetime.now()
    meta = {
        "codigo": codigo,
        "usuario": usuario,
        "fecha_hora": ahora.strftime("%d/%m/%Y %H:%M"),
        "nombre": nombre_archivo,
    }

    qr_path = _generar_qr_png(_payload_qr(codigo, nombre_archivo, ahora.isoformat(timespec="seconds")))
    pdf = None
    try:
        pdf = _ReportePDF(meta, qr_path)
        pdf.set_auto_page_break(auto=True, margin=24)
        pdf.set_margins(18, 32, 18)
        pdf.add_page()

        _portada(pdf, meta, filtros)
        _resumen_ejecutivo(pdf, est, met, resumen)
        _seccion_dataset(pdf, est)
        _seccion_modelo(pdf, met)
        _seccion_filtrado(pdf, filtros, resumen)
        _seccion_glosario_qr(pdf)

        return bytes(pdf.output())
    finally:
        if qr_path and os.path.isfile(qr_path):
            try:
                os.remove(qr_path)
            except OSError:
                pass


def generar_y_subir(filtros: dict, usuario: str) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    codigo = f"DC-{timestamp[:8]}-{secrets.token_hex(3).upper()}"
    nombre = f"reporte_{timestamp}.pdf"
    contenido = generar_pdf(filtros, usuario, codigo, nombre)
    metadatos = _subir_pdf(nombre, contenido, codigo=codigo)
    metadatos["fecha"] = datetime.now().isoformat()
    metadatos["codigo_verificacion"] = codigo
    logger.info("AUDIT reporte_generado nombre=%s codigo=%s usuario=%s filtros=%s",
                nombre, codigo, usuario, filtros)
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "create", "reportes", f"Reporte generado: {nombre} ({codigo})")
    except Exception:
        pass
    try:
        from paquetes.notificaciones.NotificacionesServicio import crear as _notif
        _notif("Reporte generado", f"Reporte {codigo} listo para descarga.", "success")
    except Exception:
        pass
    return metadatos
