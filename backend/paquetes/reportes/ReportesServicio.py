"""
ReportesServicio - reportes clínicos agregados en PDF.

Incluye estadísticas del dataset, métricas del modelo ML y resumen filtrado.
Solo datos agregados - sin identificadores de pacientes.
"""

from __future__ import annotations

import io
import json
import logging
import os
import secrets
import tempfile
import time
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
COLOR_ALERTA = (185, 28, 28)
COLOR_OK = (21, 128, 61)
COLOR_KPI_BG = (248, 250, 252)
COLOR_ALERTA = (185, 28, 28)
COLOR_OK = (21, 128, 61)
COLOR_KPI_BG = (248, 250, 252)

logger = logging.getLogger("diabcare.reportes")


# ---------------------------------------------------------------------------
# Utilidades MinIO
# ---------------------------------------------------------------------------
def _asegurar_bucket(cliente):
    if not cliente.bucket_exists(BUCKET_APP):
        cliente.make_bucket(BUCKET_APP)


def _subir_pdf(nombre: str, contenido: bytes, meta: dict | None = None) -> dict:
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
    if meta:
        meta_obj = f"{PREFIJO_REPORTES}{nombre}.meta.json"
        body = json.dumps(meta, ensure_ascii=False).encode("utf-8")
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


def _nombre_seguro(nombre: str) -> str | None:
    """Evita path traversal; solo PDF bajo el prefijo de reportes."""
    n = (nombre or "").strip().replace("\\", "/").lstrip("/")
    if not n or ".." in n or "/" in n or not n.lower().endswith(".pdf"):
        return None
    return n


def eliminar_reporte(nombre: str, usuario: str = "sistema") -> bool:
    seguro = _nombre_seguro(nombre)
    if not seguro:
        return False
    try:
        cliente = get_cliente()
        cliente.remove_object(BUCKET_APP, f"{PREFIJO_REPORTES}{seguro}")
        try:
            cliente.remove_object(BUCKET_APP, f"{PREFIJO_REPORTES}{seguro}.meta.json")
        except Exception:
            pass
        logger.info("AUDIT reporte_eliminado nombre=%s usuario=%s", seguro, usuario)
        try:
            from paquetes.auditoria.AuditoriaServicio import registrar
            registrar(usuario, "delete", "reportes", f"Reporte eliminado: {seguro}")
        except Exception:
            pass
        return True
    except Exception as e:
        logger.warning("No se pudo eliminar reporte '%s': %s", nombre, e)
        return False


def eliminar_historial_reportes(usuario: str = "sistema") -> dict:
    """Borra todos los PDF (y meta) del historial de reportes."""
    try:
        cliente = get_cliente()
        if not cliente.bucket_exists(BUCKET_APP):
            return {"eliminados": 0}
        objetos = list(cliente.list_objects(BUCKET_APP, prefix=PREFIJO_REPORTES, recursive=True))
        n = 0
        for obj in objetos:
            try:
                cliente.remove_object(BUCKET_APP, obj.object_name)
                n += 1
            except Exception:
                pass
        logger.info("AUDIT reportes_historial_vaciado n=%s usuario=%s", n, usuario)
        try:
            from paquetes.auditoria.AuditoriaServicio import registrar
            registrar(usuario, "delete", "reportes", f"Historial de reportes vaciado ({n} objetos)")
        except Exception:
            pass
        return {"eliminados": n}
    except Exception as e:
        logger.warning("No se pudo vaciar historial de reportes: %s", e)
        return {"eliminados": 0, "error": str(e)}


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
    clinicos = {
        k: v for k, v in (filtros or {}).items()
        if k not in ("tipo", "departamento") and v not in (None, "")
    }
    if not clinicos:
        return {"total": 0}
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


_OPS_MEMO: tuple[float, dict] | None = None
_OPS_TTL = 60.0


def _datos_operativos() -> dict:
    """Informes simples: consultas directas a la capa operativa (tipo SELECT)."""
    global _OPS_MEMO
    now = time.monotonic()
    if _OPS_MEMO is not None and (now - _OPS_MEMO[0]) < _OPS_TTL:
        return _OPS_MEMO[1]
    out = {}
    try:
        from paquetes.clinico.citas.CitasServicio import resumen_operativo
        out["citas"] = resumen_operativo()
    except Exception as e:
        logger.warning("Resumen de citas no disponible: %s", e)
    try:
        from paquetes.urgencias import UrgenciasServicio as U
        out["urgencias"] = U.resumen_operativo()
    except Exception as e:
        logger.warning("Resumen de urgencias no disponible: %s", e)
    try:
        from paquetes.laboratorio import LaboratorioServicio as L
        out["laboratorio"] = L.resumen_operativo()
    except Exception as e:
        logger.warning("Resumen de laboratorio no disponible: %s", e)
    try:
        from paquetes.facturacion import FacturacionServicio as F
        out["caja"] = F.resumen_caja()
    except Exception as e:
        logger.warning("Resumen de caja no disponible: %s", e)
    try:
        from paquetes.clinico.pacientes.PacientesServicio import resumen as _res_pac
        out["pacientes"] = _res_pac()
    except Exception as e:
        logger.warning("Resumen de pacientes no disponible: %s", e)
    try:
        from paquetes.clinico.admisiones.AdmisionesServicio import resumen as _res_adm
        out["admisiones"] = _res_adm()
    except Exception as e:
        logger.warning("Resumen de admisiones no disponible: %s", e)
    try:
        from paquetes.farmacia import FarmaciaServicio as Farm
        out["farmacia"] = Farm.resumen_operativo()
    except Exception as e:
        logger.warning("Resumen de farmacia no disponible: %s", e)
    try:
        from paquetes.rrhh import RrhhServicio as R
        out["rrhh"] = R.resumen_operativo()
    except Exception as e:
        logger.warning("Resumen de RRHH no disponible: %s", e)
    try:
        from paquetes.comorbilidades import ComorbilidadesServicio as C
        out["comorbilidades"] = C.resumen_operativo()
    except Exception as e:
        logger.warning("Resumen de comorbilidades no disponible: %s", e)
    _OPS_MEMO = (now, out)
    return out


def _datos_compuestos() -> dict:
    """Informes compuestos: agregados materializados por el ELT (negocio/agg_*)."""
    try:
        from paquetes.dataset.DatasetKpisServicio import informes_complejos
        return informes_complejos()
    except Exception as e:
        logger.warning("Informes compuestos no disponibles: %s", e)
        return {}


# ---------------------------------------------------------------------------
# PDF - utilidades
# ---------------------------------------------------------------------------
# Las fuentes base del PDF usan latin-1: las tildes y la eñe funcionan, pero
# viñetas, rayas largas y símbolos especiales se volverían "?" si no se
# reemplazan antes por equivalentes seguros.
_REEMPLAZOS_LATIN1 = {
    "\u2022": "-",    # • viñeta
    "\u2014": "-",    # - raya larga
    "\u2013": "-",    # - raya media
    "\u2026": "...",  # … puntos suspensivos
    "\u2018": "'", "\u2019": "'",   # comillas simples tipográficas
    "\u201c": '"', "\u201d": '"',   # comillas dobles tipográficas
    "\u2192": "->",   # → flecha
    "\u2713": "", "\u2714": "",     # ✓ ✔ checks
    "\u00a0": " ",    # espacio duro
}


def _txt(valor) -> str:
    s = str(valor)
    for raro, seguro in _REEMPLAZOS_LATIN1.items():
        s = s.replace(raro, seguro)
    return s.encode("latin-1", "replace").decode("latin-1")


def _fmt_num(n) -> str:
    try:
        return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(n)


def _fmt_money(n) -> str:
    try:
        entero, dec = f"{float(n):,.2f}".split(".")
        return "$" + entero.replace(",", ".") + "," + dec
    except (TypeError, ValueError):
        return str(n)


def _tabla(pdf: FPDF, cabeceras: list, filas: list, anchos: list, alineaciones: list | None = None):
    """Tabla compacta con cabecera resaltada y filas alternadas."""
    alineaciones = alineaciones or ["L"] * len(cabeceras)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(*COLOR_FONDO_SEC)
    pdf.set_text_color(*COLOR_PRIMARIO)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_line_width(0.15)
    for cab, w, al in zip(cabeceras, anchos, alineaciones):
        pdf.cell(w, 6.5, _txt(cab), border=1, align=al, fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*COLOR_TEXTO)
    for i, fila in enumerate(filas):
        pdf.set_fill_color(248, 250, 252) if i % 2 else pdf.set_fill_color(255, 255, 255)
        for val, w, al in zip(fila, anchos, alineaciones):
            pdf.cell(w, 6, _txt(val), border=1, align=al, fill=True)
        pdf.ln()
    pdf.ln(3)


# Claves de departamento → datos en informes simples / compuestos
_DEPTOS_SIMPLE = {
    "citas": "Agenda de citas",
    "urgencias": "Urgencias",
    "laboratorio": "Laboratorio",
    "caja": "Caja y facturación",
    "pacientes": "Padrón de pacientes",
    "admisiones": "Admisiones",
    "farmacia": "Farmacia",
    "rrhh": "RRHH y costeo",
    "comorbilidades": "Comorbilidades",
}
_DEPTOS_COMPUESTO = {
    "caja": ("ingresos_por_dia", "costo_servicio"),
    "farmacia": ("margen_farmacia", "medicamentos_top"),
    "rrhh": ("productividad_medica",),
    "urgencias": ("espera_urgencias",),
}
_TIPOS_LABEL = {
    "simple": "Informe operativo",
    "compuesto": "Informe de indicadores agregados",
    "completo": "Informe de gestión",
}


def _normalizar_alcance(filtros: dict) -> tuple[str, str]:
    """Devuelve (tipo, departamento) normalizados."""
    tipo = str(filtros.get("tipo") or "completo").strip().lower()
    if tipo not in _TIPOS_LABEL:
        tipo = "completo"
    depto = str(filtros.get("departamento") or "todos").strip().lower()
    if depto in ("", "all", "todo"):
        depto = "todos"
    return tipo, depto


def _nombre_depto(depto: str) -> str:
    if depto == "todos":
        return "Toda la operación"
    return _DEPTOS_SIMPLE.get(depto, depto.replace("_", " ").title())


def _filtrar_ops(ops: dict, departamento: str) -> dict:
    if departamento == "todos":
        return ops
    if departamento not in _DEPTOS_SIMPLE:
        return ops
    return {departamento: ops[departamento]} if departamento in ops else {}


def _filtrar_comp(comp: dict, departamento: str) -> dict:
    if departamento == "todos":
        return comp
    claves = _DEPTOS_COMPUESTO.get(departamento)
    if not claves:
        return {}
    return {k: comp.get(k) or [] for k in claves if comp.get(k)}


def _describir_filtros(filtros: dict) -> str:
    tipo, depto = _normalizar_alcance(filtros or {})
    partes = [f"{_TIPOS_LABEL[tipo]}", f"Area: {_nombre_depto(depto)}"]
    if filtros.get("diabetes") is not None:
        partes.append("Con diabetes" if filtros["diabetes"] == 1 else "Sin diabetes")
    if filtros.get("gender"):
        partes.append(f"Genero: {filtros['gender']}")
    if filtros.get("location"):
        partes.append(f"Ubicacion: {filtros['location']}")
    if filtros.get("year") is not None:
        partes.append(f"Anio {filtros['year']}")
    if filtros.get("age_min") is not None:
        partes.append(f"Edad min. {filtros['age_min']}")
    if filtros.get("age_max") is not None:
        partes.append(f"Edad max. {filtros['age_max']}")
    return "  |  ".join(partes)


def _base_publica(base_url: str | None = None) -> str:
    from nucleo.utilidades.UrlPublica import base_publica
    return base_publica(base_url)


def _url_verificacion(codigo: str, base_url: str | None = None) -> str:
    """URL corta que el QR abre en el celular."""
    return f"{_base_publica(base_url)}/v/{codigo}"


def _payload_qr(codigo: str, nombre: str, generado: str, base_url: str | None = None) -> str:
    """El QR debe ser una URL: la cámara del celular la abre directo."""
    return _url_verificacion(codigo, base_url)


def _generar_qr_png(contenido: str) -> str | None:
    try:
        import qrcode
        # URLs cortas /v/CODIGO caben en versión baja; fit=True ajusta si crece.
        qr = qrcode.QRCode(version=3, box_size=4, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
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


def _normalizar_codigo(codigo: str) -> str:
    return (codigo or "").strip().upper()


def buscar_por_codigo(codigo: str) -> dict | None:
    """Localiza un reporte por código de verificación (meta en MinIO)."""
    cod = _normalizar_codigo(codigo)
    if not cod or not cod.startswith("DC-"):
        return None
    try:
        cliente = get_cliente()
        if not cliente.bucket_exists(BUCKET_APP):
            return None
        for obj in cliente.list_objects(BUCKET_APP, prefix=PREFIJO_REPORTES, recursive=True):
            if not obj.object_name.endswith(".meta.json"):
                continue
            try:
                raw = cliente.get_object(BUCKET_APP, obj.object_name).read()
                meta = json.loads(raw)
            except Exception:
                continue
            if _normalizar_codigo(meta.get("codigo_verificacion") or "") != cod:
                continue
            nombre = meta.get("nombre") or obj.object_name.replace(PREFIJO_REPORTES, "", 1).replace(".meta.json", "")
            return {
                "valido": True,
                "codigo": cod,
                "nombre": nombre,
                "fecha": meta.get("fecha"),
                "usuario": meta.get("usuario"),
                "tipo": meta.get("tipo"),
                "departamento": meta.get("departamento"),
                "url_pdf": f"/api/reportes/verificar/{cod}/pdf",
                "url_pagina": f"/v/{cod}",
            }
    except Exception as e:
        logger.warning("buscar_por_codigo falló: %s", e)
    return None


def verificar_reporte(codigo: str) -> dict:
    hallado = buscar_por_codigo(codigo)
    if not hallado:
        return {"valido": False, "codigo": _normalizar_codigo(codigo), "detalle": "Código no encontrado"}
    return hallado


def pdf_por_codigo(codigo: str) -> tuple[bytes | None, str | None]:
    """Devuelve (contenido, nombre) si el código es válido."""
    hallado = buscar_por_codigo(codigo)
    if not hallado:
        return None, None
    nombre = hallado.get("nombre")
    contenido = descargar_reporte(nombre) if nombre else None
    return contenido, nombre


class _ReportePDF(FPDF):
    def __init__(self, meta: dict, qr_path: str | None = None):
        super().__init__()
        self.meta = meta
        self.qr_path = qr_path

    def header(self):
        # Encabezado institucional de informe de negocios
        if LOGO_PATH.is_file():
            self.image(str(LOGO_PATH), x=self.l_margin, y=9, h=12)
            tx = self.l_margin + 16
        else:
            tx = self.l_margin

        self.set_xy(tx, 9)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*COLOR_PRIMARIO)
        self.cell(0, 6, _txt("DiabCare Hospital"))
        self.ln(5)
        self.set_x(tx)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*COLOR_MUTED)
        self.cell(0, 4, _txt("Clinica especializada en diabetes  |  Informe de gestion"))

        # Franja derecha: tipo de documento
        self.set_xy(self.w - self.r_margin - 52, 9)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*COLOR_ACENTO)
        self.cell(52, 4, _txt("INFORME"), align="R")
        self.set_xy(self.w - self.r_margin - 52, 13)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*COLOR_MUTED)
        self.cell(52, 4, _txt(self.meta.get("tipo_doc", "Gestion")), align="R")

        self.set_draw_color(*COLOR_PRIMARIO)
        self.set_line_width(0.6)
        self.line(self.l_margin, 24, self.w - self.r_margin, 24)
        self.set_draw_color(*COLOR_ACENTO)
        self.set_line_width(0.25)
        self.line(self.l_margin, 25.2, self.w - self.r_margin, 25.2)
        self.set_y(30)
        self.set_text_color(*COLOR_TEXTO)

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        qr_w = 14
        if self.qr_path and os.path.isfile(self.qr_path):
            self.image(self.qr_path, x=self.l_margin, y=self.get_y(), w=qr_w)
            self.set_xy(self.l_margin + qr_w + 2, self.get_y() + 1)
            self.set_font("Helvetica", "", 6.5)
            self.set_text_color(*COLOR_MUTED)
            self.multi_cell(52, 3, _txt(
                f"Codigo {self.meta.get('codigo', '-')}\n"
                "Escanee el QR en el celular\n"
                "para verificar y ver el PDF"
            ))
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*COLOR_MUTED)
        self.set_xy(0, -10)
        self.cell(
            0, 6,
            _txt(f"Pagina {self.page_no()}  |  Documento confidencial - uso interno DiabCare"),
            align="C",
        )


def _bloque_titulo(pdf: FPDF, numero: str, titulo: str, subtitulo: str = ""):
    pdf.ln(4)
    pdf.set_fill_color(*COLOR_FONDO_SEC)
    pdf.set_draw_color(*COLOR_ACENTO)
    pdf.set_line_width(0.2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*COLOR_PRIMARIO)
    encabezado = f"  {numero}. {titulo}" if numero else f"  {titulo}"
    pdf.cell(0, 8, _txt(encabezado), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
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


def _parrafo(pdf: FPDF, texto: str, espacio: float = 3):
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*COLOR_TEXTO)
    pdf.multi_cell(0, 5, _txt(texto))
    pdf.ln(espacio)


def _subtitulo_area(pdf: FPDF, titulo: str):
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*COLOR_PRIMARIO)
    pdf.cell(0, 7, _txt(titulo), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*COLOR_TEXTO)
    pdf.ln(1)


def _accion(pdf: FPDF, texto: str):
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.multi_cell(0, 4.5, _txt(f"Atención: {texto}"))
    pdf.set_text_color(*COLOR_TEXTO)
    pdf.ln(4)


def _portada(pdf: FPDF, meta: dict, filtros: dict):
    tipo, depto = _normalizar_alcance(filtros or {})
    area = _nombre_depto(depto)
    tipo_label = _TIPOS_LABEL.get(tipo, "Informe")

    # Titulo principal del documento
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*COLOR_TEXTO)
    pdf.multi_cell(0, 8, _txt(area))
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*COLOR_PRIMARIO)
    pdf.cell(0, 6, _txt(tipo_label), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # Caja de metadatos (estilo ficha de informe)
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_line_width(0.2)
    y0 = pdf.get_y()
    pdf.rect(pdf.l_margin, y0, pdf.epw, 22, style="DF")
    pdf.set_xy(pdf.l_margin + 3, y0 + 2.5)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*COLOR_MUTED)
    filas_meta = [
        ("Codigo", meta.get("codigo", "-")),
        ("Fecha de emision", meta.get("fecha_hora", "-")),
        ("Elaborado por", meta.get("usuario", "-")),
        ("Alcance", _describir_filtros(filtros)),
    ]
    col_w = (pdf.epw - 6) / 2
    for i, (lab, val) in enumerate(filas_meta):
        col = i % 2
        row = i // 2
        x = pdf.l_margin + 3 + col * col_w
        y = y0 + 2.5 + row * 9
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*COLOR_MUTED)
        pdf.cell(col_w - 4, 3, _txt(lab))
        pdf.set_xy(x, y + 3)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*COLOR_TEXTO)
        pdf.cell(col_w - 4, 4, _txt(val)[:48])
    pdf.set_y(y0 + 24)
    pdf.set_text_color(*COLOR_TEXTO)



def _fila_kpis(pdf: FPDF, tarjetas: list[tuple[str, str, str]]):
    """Dibuja hasta 4 KPIs en una fila. Cada item: (etiqueta, valor, tono).
    tono: 'alerta' | 'ok' | 'neutro'
    """
    if not tarjetas:
        return
    n = min(len(tarjetas), 4)
    gap = 3
    w = (pdf.epw - gap * (n - 1)) / n
    h = 22
    y0 = pdf.get_y()
    x0 = pdf.l_margin
    for i, (lab, val, tono) in enumerate(tarjetas[:n]):
        x = x0 + i * (w + gap)
        pdf.set_fill_color(*COLOR_KPI_BG)
        pdf.set_draw_color(203, 213, 225)
        pdf.set_line_width(0.2)
        pdf.rect(x, y0, w, h, style="DF")
        if tono == "alerta":
            pdf.set_fill_color(*COLOR_ALERTA)
        elif tono == "ok":
            pdf.set_fill_color(*COLOR_OK)
        else:
            pdf.set_fill_color(*COLOR_PRIMARIO)
        pdf.rect(x, y0, 1.2, h, style="F")
        pdf.set_xy(x + 4, y0 + 3)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*COLOR_MUTED)
        pdf.cell(w - 6, 4, _txt(lab)[:28])
        pdf.set_xy(x + 4, y0 + 9)
        pdf.set_font("Helvetica", "B", 13)
        if tono == "alerta":
            pdf.set_text_color(*COLOR_ALERTA)
        elif tono == "ok":
            pdf.set_text_color(*COLOR_OK)
        else:
            pdf.set_text_color(*COLOR_TEXTO)
        pdf.cell(w - 6, 8, _txt(val)[:18])
    pdf.set_y(y0 + h + 6)
    pdf.set_text_color(*COLOR_TEXTO)


def _construir_kpis(ops: dict, comp: dict, est: dict | None = None) -> list[tuple[str, str, str]]:
    ops = ops or {}
    comp = comp or {}
    tarjetas = []

    caja = ops.get("caja") or {}
    if caja:
        pend = float(caja.get("monto_pendiente") or 0)
        tarjetas.append(("Por cobrar", _fmt_money(pend), "alerta" if pend > 0 else "ok"))

    farm = ops.get("farmacia") or {}
    if farm:
        pend = int(farm.get("recetas_pendientes") or 0)
        tarjetas.append(("Recetas en cola", _fmt_num(pend), "alerta" if pend > 0 else "ok"))

    urg = ops.get("urgencias") or {}
    if urg:
        espera = int(urg.get("en_atencion_o_espera") or 0)
        tarjetas.append(("Urgencias en espera", _fmt_num(espera), "alerta" if espera > 0 else "ok"))

    lab = ops.get("laboratorio") or {}
    if lab:
        pend = int(lab.get("ordenes_pendientes") or 0)
        tarjetas.append(("Ordenes de lab", _fmt_num(pend), "alerta" if pend > 0 else "ok"))

    adm = ops.get("admisiones") or {}
    if adm and len(tarjetas) < 4:
        act = int(adm.get("activas") or 0)
        tarjetas.append(("Hospitalizados", _fmt_num(act), "neutro"))

    ing = comp.get("ingresos_por_dia") or []
    if ing and len(tarjetas) < 4:
        total = sum(float(d.get("total") or 0) for d in ing)
        tarjetas.append(("Facturado (periodo)", _fmt_money(total), "neutro"))

    if est and est.get("total") and len(tarjetas) < 4:
        total = int(est["total"])
        con = int(est.get("con_diabetes") or 0)
        pct = round(con / total * 100, 1) if total else 0
        tarjetas.append(("% con diabetes", f"{pct}%", "neutro"))

    return tarjetas[:4]


def _construir_prioridades(ops: dict) -> list[tuple[str, str, int]]:
    """Peso fijo por criticidad clinica/operativa (no por monto bruto)."""
    ops = ops or {}
    out = []

    urg = ops.get("urgencias") or {}
    espera = int(urg.get("en_atencion_o_espera") or 0)
    if espera > 0:
        out.append(("Urgencias", f"Atender cola de {_fmt_num(espera)} pacientes en triage/espera.", 100))

    lab = ops.get("laboratorio") or {}
    pend_lab = int(lab.get("ordenes_pendientes") or 0)
    if pend_lab > 0:
        out.append(("Laboratorio", f"Despachar {_fmt_num(pend_lab)} ordenes pendientes.", 90))

    farm = ops.get("farmacia") or {}
    pend_rx = int(farm.get("recetas_pendientes") or 0)
    stock = int(farm.get("stock_bajo") or 0)
    if pend_rx > 0:
        out.append(("Farmacia", f"Dispensar {_fmt_num(pend_rx)} recetas en cola.", 80))
    if stock > 0:
        out.append(("Farmacia / stock", f"Reponer {_fmt_num(stock)} medicamentos bajo minimo.", 70))

    caja = ops.get("caja") or {}
    monto = float(caja.get("monto_pendiente") or 0)
    if monto > 0:
        out.append(("Caja", f"Cobrar cartera pendiente de {_fmt_money(monto)}.", 60))

    citas = ops.get("citas") or {}
    if citas and int(citas.get("total") or 0) <= 0:
        out.append(("Agenda", "Sin turnos hoy: revisar programacion o rango de fechas.", 20))
    elif citas:
        cobro_p = int(citas.get("cobro_pendiente") or 0)
        if cobro_p > 0:
            out.append(("Agenda", f"Gestionar cobro de {_fmt_num(cobro_p)} consultas.", 50))

    com = ops.get("comorbilidades") or {}
    if com and com.get("tipo_mas_frecuente") and int(com.get("total") or 0) > 0:
        out.append((
            "Clinica",
            f"Seguimiento prioritario: {com.get('tipo_mas_frecuente')} "
            f"({_fmt_num(com.get('total', 0))} casos activos).",
            40,
        ))

    out.sort(key=lambda x: x[2], reverse=True)
    return out[:6]


def _seccion_kpis(pdf: FPDF, ops: dict, comp: dict, est: dict | None = None):
    _bloque_titulo(pdf, "", "Indicadores clave")
    tarjetas = _construir_kpis(ops, comp, est)
    if not tarjetas:
        _parrafo(pdf, "No hay indicadores disponibles para el alcance seleccionado.")
        return
    _fila_kpis(pdf, tarjetas)


def _seccion_prioridades(pdf: FPDF, ops: dict, numero: str = "1"):
    _bloque_titulo(pdf, numero, "Prioridades de gestion",
                   "Lo que requiere atencion inmediata, ordenado por impacto.")
    items = _construir_prioridades(ops)
    if not items:
        _parrafo(pdf, "Sin alertas operativas. Las areas consultadas operan dentro de lo esperado.")
        return
    for i, (area, accion, _) in enumerate(items, 1):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*COLOR_PRIMARIO)
        pdf.cell(0, 6, _txt(f"{i}. {area}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*COLOR_TEXTO)
        pdf.multi_cell(0, 5, _txt(accion))
        pdf.ln(2)


def _resumen_ejecutivo(pdf: FPDF, est: dict, met: dict, resumen: dict,
                       ops: dict | None = None, comp: dict | None = None,
                       *, incluir_analitica: bool = False):
    """Lectura de una mirada: el hallazgo principal, sin relleno."""
    _bloque_titulo(pdf, "", "En una mirada")
    ops = ops or {}
    prioridades = _construir_prioridades(ops)
    if prioridades:
        area, accion, _ = prioridades[0]
        texto = f"Prioridad actual: {area}. {accion}"
        if len(prioridades) > 1:
            texto += f" Hay {_fmt_num(len(prioridades))} frentes que requieren seguimiento."
    else:
        texto = (
            "Sin alertas operativas criticas en el alcance seleccionado. "
            "Revise los indicadores clave y el desempeno del periodo."
        )
    _parrafo(pdf, texto)


def _brief_simple(clave: str, datos: dict) -> tuple[str, str, str] | None:
    """(titulo, situación, atención) - o None si no hay datos."""
    if not datos:
        return None
    if clave == "citas":
        total = int(datos.get("total") or 0)
        pend = int(datos.get("cobro_pendiente") or 0)
        pag = int(datos.get("cobro_pagado") or 0)
        if total <= 0:
            sit = (
                f"No hay turnos registrados para la fecha "
                f"{datos.get('fecha', 'consultada')}."
            )
            acc = "Verificar la agenda o ampliar el rango de fechas."
        else:
            sit = (
                f"La agenda del {datos.get('fecha', 'dia')} tiene {_fmt_num(total)} turnos: "
                f"{_fmt_num(pag)} ya cobrados y {_fmt_num(pend)} con cobro pendiente."
            )
            acc = (
                f"Gestionar el cobro de {_fmt_num(pend)} consultas pendientes."
                if pend else "No hay cobros pendientes en la agenda del dia."
            )
        return ("Agenda de citas", sit, acc)
    if clave == "urgencias":
        total = int(datos.get("total") or 0)
        espera = int(datos.get("en_atencion_o_espera") or 0)
        atend = int(datos.get("atendidas") or 0)
        sit = (
            f"De {_fmt_num(total)} urgencias registradas, {_fmt_num(atend)} ya fueron atendidas "
            f"y {_fmt_num(espera)} permanecen en triage o espera."
        )
        acc = (
            f"Priorizar la cola de {_fmt_num(espera)} pacientes en espera."
            if espera else "No hay cola acumulada en urgencias."
        )
        return ("Urgencias", sit, acc)
    if clave == "laboratorio":
        pend = int(datos.get("ordenes_pendientes") or 0)
        comp = int(datos.get("ordenes_completadas") or 0)
        sit = (
            f"Laboratorio tiene {_fmt_num(pend)} órdenes pendientes y "
            f"{_fmt_num(comp)} completadas, con {_fmt_num(datos.get('resultados_registrados', 0))} "
            f"resultados cargados."
        )
        acc = (
            f"Despachar {_fmt_num(pend)} órdenes pendientes para evitar retrasos clínicos."
            if pend else "No hay órdenes pendientes de laboratorio."
        )
        return ("Laboratorio", sit, acc)
    if clave == "caja":
        pend = float(datos.get("monto_pendiente") or 0)
        sit = (
            f"Hay {_fmt_num(datos.get('total_facturas', 0))} facturas vigentes "
            f"({_fmt_num(datos.get('pagadas', 0))} pagadas). "
            f"Cartera por cobrar: {_fmt_money(pend)}."
        )
        acc = (
            f"Dar seguimiento a la cartera pendiente de {_fmt_money(pend)}."
            if pend > 0 else "No hay montos pendientes de cobro."
        )
        return ("Caja y facturación", sit, acc)
    if clave == "pacientes":
        sit = (
            f"El padrón tiene {_fmt_num(datos.get('total', 0))} pacientes "
            f"({_fmt_num(datos.get('activos', 0))} activos"
            + (f", {_fmt_num(datos.get('inactivos', 0))} inactivos" if datos.get("inactivos") else "")
            + ")."
        )
        return ("Padrón de pacientes", sit, "Mantener actualizados los expedientes con datos demográficos.")
    if clave == "admisiones":
        act = int(datos.get("activas") or 0)
        sit = (
            f"Hay {_fmt_num(act)} pacientes hospitalizados y "
            f"{_fmt_num(datos.get('altas', 0))} altas registradas "
            f"(total histórico {_fmt_num(datos.get('total', 0))})."
        )
        acc = (
            f"Revisar ocupación: {_fmt_num(act)} admisiones activas."
            if act else "No hay hospitalizaciones activas."
        )
        return ("Admisiones", sit, acc)
    if clave == "farmacia":
        pend = int(datos.get("recetas_pendientes") or 0)
        stock = int(datos.get("stock_bajo") or 0)
        sit = (
            f"De {_fmt_num(datos.get('recetas_total', 0))} recetas, "
            f"{_fmt_num(pend)} esperan dispensación y "
            f"{_fmt_num(datos.get('recetas_dispensadas', 0))} ya se completaron. "
            f"Ventas del periodo: {_fmt_money(datos.get('ventas_total', 0))}."
        )
        partes_acc = []
        if pend:
            partes_acc.append(f"despejar la cola de {_fmt_num(pend)} recetas")
        if stock:
            partes_acc.append(f"reponer {_fmt_num(stock)} medicamentos bajo mínimo")
        acc = ("Priorizar: " + " y ".join(partes_acc) + ".") if partes_acc else "Sin alertas de cola ni de stock."
        return ("Farmacia", sit, acc)
    if clave == "rrhh":
        sit = (
            f"{_fmt_num(datos.get('personal_costeado', 0))} colaboradores con costeo activo "
            f"(costo hora promedio {_fmt_money(datos.get('costo_hora_promedio', 0))}). "
            f"En el periodo se registraron {_fmt_num(datos.get('consultas_periodo', 0))} consultas "
            f"que generaron {_fmt_money(datos.get('ingreso_generado', 0))}."
        )
        return ("RRHH y costeo", sit, "Contrastar ingreso generado frente al costo hora del personal clínico.")
    if clave == "comorbilidades":
        sit = (
            f"{_fmt_num(datos.get('total', 0))} complicaciones activas en "
            f"{_fmt_num(datos.get('pacientes_afectados', 0))} pacientes. "
            f"La más frecuente es {datos.get('tipo_mas_frecuente') or 'sin dato'}."
        )
        return ("Comorbilidades", sit, "Priorizar seguimiento clínico del tipo más frecuente.")
    return None


def _seccion_dataset(pdf: FPDF, est: dict, numero: str = "1"):
    """Contexto clinico breve (sin jerga de dataset)."""
    total = est.get("total", 0)
    if not total:
        return
    con = est.get("con_diabetes", 0)
    pct = round(con / total * 100, 1) if total else 0
    prom = est.get("promedios", {}) or {}
    hba = prom.get("hba1c", {}) or {}
    glu = prom.get("glucosa", {}) or {}
    _bloque_titulo(pdf, numero, "Contexto clinico",
                   "Referencia de la poblacion analizada (datos anonimizados).")
    _parrafo(pdf,
        f"El {pct}% de la poblacion de referencia presenta diabetes "
        f"({_fmt_num(con)} de {_fmt_num(total)}). "
        f"En el grupo con diabetes, HbA1c promedio {hba.get('con', '-')}% "
        f"y glucosa {glu.get('con', '-')} mg/dL "
        f"(sin diabetes: {hba.get('sin', '-')}% / {glu.get('sin', '-')} mg/dL)."
    )


def _seccion_informes_simples(pdf: FPDF, ops: dict, numero: str = "2"):
    orden = ["citas", "urgencias", "laboratorio", "caja", "pacientes",
             "admisiones", "farmacia", "rrhh", "comorbilidades"]
    briefs = []
    for k in orden:
        b = _brief_simple(k, ops.get(k) or {})
        if b:
            briefs.append(b)

    if not briefs:
        _bloque_titulo(pdf, numero, "Situacion del area",
                       "Indicadores y acciones recomendadas.")
        _parrafo(pdf, "No hay datos operativos disponibles para el alcance seleccionado.")
        return

    # Un solo departamento: detalle completo.
    if len(briefs) == 1:
        _bloque_titulo(pdf, numero, "Situacion del area",
                       "Indicadores y acciones recomendadas.")
        titulo, sit, acc = briefs[0]
        _subtitulo_area(pdf, titulo)
        _parrafo(pdf, sit)
        _accion(pdf, acc)
        return

    # Varios departamentos: el detalle truncado no aporta; ya van prioridades/KPIs.
    return


def _seccion_informes_compuestos(pdf: FPDF, comp: dict, numero: str = "3"):
    _bloque_titulo(pdf, numero, "Desempeno del periodo",
                   "Ingresos, margenes y tiempos relevantes.")

    if not comp or not any(comp.values()):
        _parrafo(pdf, "No hay indicadores agregados disponibles para este alcance.")
        return

    ing = comp.get("ingresos_por_dia") or []
    if ing:
        total = sum(float(d.get("total") or 0) for d in ing)
        pico = max(ing, key=lambda d: float(d.get("total") or 0))
        _subtitulo_area(pdf, "Ingresos por día")
        _parrafo(pdf,
            f"En {_fmt_num(len(ing))} días con actividad se facturaron {_fmt_money(total)}. "
            f"El pico fue {pico.get('fecha')} con {_fmt_money(pico.get('total'))}."
        )

    prod = comp.get("productividad_medica") or []
    if prod:
        _subtitulo_area(pdf, "Productividad medica")
        top3 = sorted(prod, key=lambda r: float(r.get("ingreso_generado") or 0), reverse=True)[:5]
        total_ing = sum(float(r.get("ingreso_generado") or 0) for r in prod)
        total_c = sum(int(r.get("num_consultas") or 0) for r in prod)
        _parrafo(pdf,
            f"En el periodo se generaron {_fmt_money(total_ing)} con "
            f"{_fmt_num(total_c)} consultas. Ranking por ingreso (top 5):"
        )
        _tabla(pdf,
               ["#", "Periodo", "Consultas", "Ingreso"],
               [[str(i), r.get("periodo", ""),
                 _fmt_num(r.get("num_consultas", 0)),
                 _fmt_money(r.get("ingreso_generado", 0))] for i, r in enumerate(top3, 1)],
               [20, 40, 40, 50],
               ["C", "C", "R", "R"])

    mar = comp.get("margen_farmacia") or []
    if mar:
        _subtitulo_area(pdf, "Margen de farmacia")
        top = sorted(mar, key=lambda r: float(r.get("margen") or 0), reverse=True)[:5]
        mejor = top[0]
        _parrafo(pdf,
            f"El mejor margen corresponde a {mejor.get('medicamento', '-')} "
            f"({_fmt_money(mejor.get('margen', 0))} en {mejor.get('periodo', '')})."
        )
        _tabla(pdf,
               ["Medicamento", "Periodo", "Margen"],
               [[str(r.get("medicamento", ""))[:32], r.get("periodo", ""),
                 _fmt_money(r.get("margen", 0))] for r in top],
               [80, 40, 40],
               ["L", "C", "R"])

    top = comp.get("medicamentos_top") or []
    if top and not mar:  # si ya hay margen, el top es redundante
        _subtitulo_area(pdf, "Medicamentos más dispensados")
        _tabla(pdf,
               ["Medicamento", "Periodo", "Dispensaciones"],
               [[str(r.get("nombre", ""))[:40], r.get("periodo", ""),
                 _fmt_num(r.get("total_dispensaciones", 0))] for r in top[:5]],
               [90, 40, 36],
               ["L", "C", "R"])

    esp = comp.get("espera_urgencias") or []
    if esp:
        e0 = esp[0]
        _subtitulo_area(pdf, "Tiempos de espera en urgencias")
        _parrafo(pdf,
            f"En el periodo {e0.get('periodo', '')} la espera promedio fue "
            f"{e0.get('espera_promedio_min', 0)} minutos sobre "
            f"{_fmt_num(e0.get('total_urgencias', 0))} urgencias."
        )

    cos = comp.get("costo_servicio") or []
    if cos:
        _subtitulo_area(pdf, "Costo frente a lo facturado")
        top = sorted(cos, key=lambda r: float(r.get("margen") or 0), reverse=True)[:5]
        _tabla(pdf,
               ["Servicio", "Periodo", "Margen"],
               [[str(r.get("servicio", ""))[:28], r.get("periodo", ""),
                 _fmt_money(r.get("margen", 0))] for r in top],
               [80, 40, 40],
               ["L", "C", "R"])


def _seccion_modelo(pdf: FPDF, met: dict, numero: str = "4"):
    _bloque_titulo(pdf, numero, "Modelo predictivo",
                   "Rendimiento del algoritmo en datos de prueba.")
    if not met or "error" in met:
        _parrafo(pdf, "El modelo aún no está entrenado. Use el módulo Modelo ML para generar métricas.")
        return
    _parrafo(pdf,
        f"Exactitud {met.get('accuracy', '-')}, precisión {met.get('precision', '-')}, "
        f"sensibilidad {met.get('recall', '-')} y F1 {met.get('f1', '-')}. "
        f"Entrenado con {_fmt_num(met.get('registros_entrenamiento', '-'))} registros "
        f"y evaluado con {_fmt_num(met.get('registros_prueba', '-'))}."
    )


def _seccion_filtrado(pdf: FPDF, filtros: dict, resumen: dict, numero: str = "5"):
    # Solo tiene sentido si hay filtros clínicos reales (más allá de tipo/depto)
    clinicos = {k: v for k, v in (filtros or {}).items()
                if k not in ("tipo", "departamento") and v is not None and v != ""}
    if not clinicos:
        return
    _bloque_titulo(pdf, numero, "Subconjunto filtrado")
    total = resumen.get("total", 0)
    if not total:
        _parrafo(pdf, "Ningún registro coincide con los filtros clínicos indicados.")
        return
    con = resumen.get("con_diabetes", 0)
    pct = round(con / total * 100, 1) if total else 0
    prom = resumen.get("promedios", {}) or {}
    _parrafo(pdf,
        f"Con los filtros aplicados ({_describir_filtros(filtros)}) se analizaron "
        f"{_fmt_num(total)} registros ({pct}% con diabetes). "
        f"Promedios del subconjunto: BMI {prom.get('bmi', '-')}, "
        f"HbA1c {prom.get('hba1c', '-')}%, glucosa {prom.get('glucosa', '-')} mg/dL."
    )


def _ajustar(pdf: FPDF, texto, ancho: float) -> str:
    """Recorta el texto para que entre en la celda sin desbordar la columna."""
    t = _txt(texto)
    if pdf.get_string_width(t) <= ancho - 2:
        return t
    while t and pdf.get_string_width(t + "...") > ancho - 2:
        t = t[:-1]
    return (t + "...") if t else ""


def _tabla_detalle(pdf: FPDF, cabeceras: list, filas: list, pesos: list,
                   alineaciones: list, alto: float = 5.4):
    """
    Tabla de registros reales, con anchos proporcionales al ancho util y
    cabecera repetida en cada pagina (un listado largo cruza varias hojas).
    """
    total_peso = sum(pesos) or 1
    anchos = [pdf.epw * p / total_peso for p in pesos]

    def _cabecera():
        pdf.set_font("Helvetica", "B", 7.2)
        pdf.set_fill_color(*COLOR_FONDO_SEC)
        pdf.set_text_color(*COLOR_PRIMARIO)
        pdf.set_draw_color(203, 213, 225)
        pdf.set_line_width(0.15)
        for cab, w, al in zip(cabeceras, anchos, alineaciones):
            pdf.cell(w, 6, _ajustar(pdf, cab, w), border=1, align=al, fill=True)
        pdf.ln()

    def _cuerpo():
        pdf.set_font("Helvetica", "", 6.9)
        pdf.set_text_color(*COLOR_TEXTO)

    _cabecera()
    _cuerpo()
    for i, fila in enumerate(filas):
        if pdf.will_page_break(alto):
            pdf.add_page()
            _cabecera()
            _cuerpo()
        pdf.set_fill_color(248, 250, 252) if i % 2 else pdf.set_fill_color(255, 255, 255)
        for val, w, al in zip(fila, anchos, alineaciones):
            pdf.cell(w, alto, _ajustar(pdf, val, w), border=1, align=al, fill=True)
        pdf.ln()
    pdf.ln(2)


def _bloque_detalle(pdf: FPDF, bloque: dict):
    """Pinta un bloque de detalle declarando origen y cobertura."""
    if not bloque:
        return
    _subtitulo_area(pdf, bloque["titulo"])
    if bloque.get("error"):
        _parrafo(pdf, f"No se pudo leer {bloque.get('objeto', 'la fuente')}: {bloque['error']}")
        return
    if not bloque["filas"]:
        _parrafo(pdf, f"Sin registros en {bloque['objeto']} para el alcance solicitado.")
        return
    if bloque["truncado"]:
        detalle_cob = (
            f"Mostrando {_fmt_num(bloque['mostradas'])} de {_fmt_num(bloque['total'])} "
            f"registros que cumplen el filtro. Origen: {bloque['objeto']}."
        )
    else:
        detalle_cob = (
            f"{_fmt_num(bloque['total'])} registros (listado completo). "
            f"Origen: {bloque['objeto']}."
        )
    _parrafo(pdf, detalle_cob, espacio=1)
    _tabla_detalle(pdf, bloque["cabeceras"], bloque["filas"],
                   bloque["pesos"], bloque["alineaciones"])


def _seccion_detalle_operativo(pdf: FPDF, depto: str, filtros: dict, cron,
                               numero: str = "1"):
    """Registros reales de cada area en alcance (no contadores agregados)."""
    from paquetes.reportes import ReportesDatos as RD

    claves = list(RD.FUENTES) if depto == "todos" else [depto]
    claves = [c for c in claves if c in RD.FUENTES]
    _bloque_titulo(pdf, numero, "Detalle operativo",
                   "Registros tal como estan almacenados en MinIO.")
    if not claves:
        _parrafo(pdf, "El area solicitada no tiene una fuente de detalle asociada.")
        return
    for clave in claves:
        try:
            bloque = RD.detalle(clave, filtros, cron)
        except Exception as e:
            logger.warning("Detalle de %s no disponible: %s", clave, e)
            continue
        _bloque_detalle(pdf, bloque)


def _seccion_detalle_clinico(pdf: FPDF, filtros: dict, cron, numero: str = "2"):
    """Encuentros clinicos del stage con los filtros del informe aplicados."""
    from paquetes.reportes import ReportesDatos as RD

    _bloque_titulo(pdf, numero, "Detalle clinico",
                   "Encuentros del dataset que cumplen los filtros del informe.")
    try:
        bloque = RD.detalle_clinico(filtros, cron)
    except Exception as e:
        logger.warning("Detalle clinico no disponible: %s", e)
        _parrafo(pdf, "No se pudo leer el dataset clinico desde MinIO.")
        return
    _bloque_detalle(pdf, bloque)


def _seccion_trazabilidad(pdf: FPDF, cron, numero: str = "9"):
    """Coste real de armar el informe, fuente por fuente."""
    _bloque_titulo(pdf, numero, "Trazabilidad y rendimiento",
                   "Que se leyo de MinIO y cuanto costo cada etapa.")
    filas = cron.como_filas()
    if not filas:
        _parrafo(pdf, "No se registraron lecturas de MinIO para este informe.")
        return
    _parrafo(pdf,
        "Cada fila es un objeto Parquet leido directamente de MinIO (sin cache), "
        "con el tiempo de descarga, el de parseo a tabla y el de filtrado.",
        espacio=1,
    )
    _tabla_detalle(
        pdf,
        ["Fuente", "Objeto en MinIO", "Tam.", "Filas", "Filtr.",
         "MinIO", "Parseo", "Filtro"],
        filas,
        [1.8, 4.2, 0.8, 0.95, 0.95, 0.7, 0.7, 0.7],
        ["L", "L", "R", "R", "R", "R", "R", "R"],
    )
    t = cron.totales()
    _parrafo(pdf,
        f"Total: {t['fuentes']} fuentes, {_fmt_num(t['filas_origen'])} filas leidas "
        f"({t['bytes_leidos'] / 1024 / 1024:.1f} MB). "
        f"MinIO {t['ms_minio']:.0f} ms + parseo {t['ms_parseo']:.0f} ms + "
        f"filtrado {t['ms_filtro']:.0f} ms. "
        f"Armado total del documento: {cron.ms_transcurrido:.0f} ms.",
        espacio=1,
    )


def _seccion_cierre(pdf: FPDF, numero: str = "6"):
    _bloque_titulo(pdf, numero, "Cierre")
    _parrafo(pdf,
        "Documento generado automaticamente por DiabCare Hospital. "
        "Los indicadores corresponden al alcance indicado en la portada. "
        "Conserve el codigo de verificacion del pie de pagina.",
        espacio=1,
    )


def generar_pdf(
    filtros: dict,
    usuario: str,
    codigo: str,
    nombre_archivo: str,
    base_url: str | None = None,
) -> bytes:
    filtros = filtros or {}
    tipo, depto = _normalizar_alcance(filtros)
    # Analitica (dataset/ML) solo en informe de gestion global, no en un area puntual
    incluir_analitica = tipo == "completo" and depto == "todos"
    incluir_simple = tipo in ("simple", "completo")
    incluir_compuesto = tipo in ("compuesto", "completo")
    clinicos = {
        k: v for k, v in filtros.items()
        if k not in ("tipo", "departamento") and v is not None and v != ""
    }

    from paquetes.reportes.ReportesDatos import Cronometro
    cron = Cronometro()

    est = _estadisticas_dataset() if incluir_analitica else {}
    met = _metricas_modelo() if incluir_analitica else {}
    resumen = _resumen_filtrado(filtros) if incluir_analitica and clinicos else {}
    ops = _filtrar_ops(_datos_operativos(), depto) if incluir_simple else {}
    comp = _filtrar_comp(_datos_compuestos(), depto) if incluir_compuesto else {}
    ahora = datetime.now()
    url_v = _url_verificacion(codigo, base_url)
    meta = {
        "codigo": codigo,
        "usuario": usuario,
        "fecha_hora": ahora.strftime("%d/%m/%Y %H:%M"),
        "nombre": nombre_archivo,
        "tipo_doc": _TIPOS_LABEL.get(tipo, "Informe"),
        "area": _nombre_depto(depto),
        "url_verificacion": url_v,
    }

    qr_path = _generar_qr_png(
        _payload_qr(codigo, nombre_archivo, ahora.isoformat(timespec="seconds"), base_url)
    )
    pdf = None
    try:
        pdf = _ReportePDF(meta, qr_path)
        pdf.set_auto_page_break(auto=True, margin=24)
        pdf.set_margins(18, 34, 18)
        pdf.add_page()

        _portada(pdf, meta, filtros)
        _seccion_kpis(pdf, ops, comp, est if incluir_analitica else None)

        n = 1
        # El nucleo del informe es el detalle: los registros como estan en MinIO.
        if incluir_simple:
            _seccion_detalle_operativo(pdf, depto, filtros, cron, numero=str(n))
            n += 1
        if incluir_analitica or clinicos:
            _seccion_detalle_clinico(pdf, filtros, cron, numero=str(n))
            n += 1
        if incluir_compuesto and (depto == "todos" or depto in _DEPTOS_COMPUESTO):
            _seccion_informes_compuestos(pdf, comp, numero=str(n))
            n += 1
        if incluir_analitica:
            _seccion_dataset(pdf, est, numero=str(n))
            n += 1
            if clinicos:
                _seccion_filtrado(pdf, filtros, resumen, numero=str(n))
                n += 1
        # Detalle ML (exactitud/F1) no aporta a un informe de gestion: se omite.
        _seccion_trazabilidad(pdf, cron, numero=str(n))
        n += 1
        _seccion_cierre(pdf, numero=str(n))

        return bytes(pdf.output())
    finally:
        if qr_path and os.path.isfile(qr_path):
            try:
                os.remove(qr_path)
            except OSError:
                pass


def generar_y_subir(filtros: dict, usuario: str, base_url: str | None = None) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    codigo = f"DC-{timestamp[:8]}-{secrets.token_hex(3).upper()}"
    tipo, depto = _normalizar_alcance(filtros or {})
    sufijo = tipo if depto == "todos" else f"{tipo}_{depto}"
    nombre = f"reporte_{sufijo}_{timestamp}.pdf"
    contenido = generar_pdf(filtros, usuario, codigo, nombre, base_url=base_url)
    fecha = datetime.now().isoformat()
    meta_store = {
        "codigo_verificacion": codigo,
        "nombre": nombre,
        "fecha": fecha,
        "usuario": usuario,
        "tipo": tipo,
        "departamento": depto,
        "url_verificacion": _url_verificacion(codigo, base_url),
    }
    metadatos = _subir_pdf(nombre, contenido, meta=meta_store)
    metadatos["fecha"] = fecha
    metadatos["codigo_verificacion"] = codigo
    metadatos["url_verificacion"] = meta_store["url_verificacion"]
    logger.info("AUDIT reporte_generado nombre=%s codigo=%s usuario=%s filtros=%s",
                nombre, codigo, usuario, filtros)
    try:
        from paquetes.auditoria.AuditoriaServicio import registrar
        registrar(usuario, "create", "reportes", f"Reporte generado: {nombre} ({codigo})")
    except Exception:
        pass
    try:
        from paquetes.notificaciones.NotificacionesServicio import emitir_a_roles
        emitir_a_roles(
            "Reporte generado",
            f"Reporte {codigo} listo para descarga.",
            "success",
            roles=["analista", "administrador"],
            canal="in_app",
            referencia_tipo="reporte",
            referencia_id=str(codigo),
        )
    except Exception:
        pass
    return metadatos
