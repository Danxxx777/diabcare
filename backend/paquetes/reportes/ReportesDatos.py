# -*- coding: utf-8 -*-
"""
Detalle real de los informes: filas del Parquet en MinIO, no resúmenes.

Los informes se armaban con `resumen_operativo()` de cada módulo, que devuelve
contadores agregados; el PDF terminaba siendo prosa ("la agenda tiene N turnos").
Aquí se leen las filas tal como están en MinIO y se mide, por fuente, cuánto
tarda la descarga del objeto, el parseo a DataFrame y el filtrado — que es el
dato de rendimiento que el informe debe poder demostrar.

La lectura es directa contra MinIO a propósito: pasar por ParquetCache daría
tiempos de caché en memoria, no de la base.
"""
from __future__ import annotations

import io
import time
from dataclasses import dataclass, field

import pandas as pd

from paquetes.configuracion.ConfiguracionAjustes import MINIO_BUCKET, MINIO_STAGE_PATH
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"

# Filas por tabla en el PDF. Por encima se corta y el informe lo declara.
LIMITE_FILAS = 60
# Tope de seguridad para el detalle clínico (el stage puede tener millones).
LIMITE_CLINICO = 120


@dataclass
class Medicion:
    """Coste de traer una fuente desde MinIO."""
    fuente: str
    objeto: str
    bytes_leidos: int = 0
    filas_origen: int = 0
    filas_filtradas: int = 0
    ms_minio: float = 0.0
    ms_parseo: float = 0.0
    ms_filtro: float = 0.0
    error: str = ""

    @property
    def ms_total(self) -> float:
        return self.ms_minio + self.ms_parseo + self.ms_filtro


@dataclass
class Cronometro:
    """Acumula las mediciones de todas las fuentes de un informe."""
    mediciones: list[Medicion] = field(default_factory=list)
    _t0: float = field(default_factory=time.perf_counter)

    def añadir(self, m: Medicion) -> None:
        self.mediciones.append(m)

    @property
    def ms_transcurrido(self) -> float:
        return (time.perf_counter() - self._t0) * 1000

    def totales(self) -> dict:
        return {
            "fuentes": len(self.mediciones),
            "bytes_leidos": sum(m.bytes_leidos for m in self.mediciones),
            "filas_origen": sum(m.filas_origen for m in self.mediciones),
            "filas_filtradas": sum(m.filas_filtradas for m in self.mediciones),
            "ms_minio": round(sum(m.ms_minio for m in self.mediciones), 1),
            "ms_parseo": round(sum(m.ms_parseo for m in self.mediciones), 1),
            "ms_filtro": round(sum(m.ms_filtro for m in self.mediciones), 1),
        }

    def como_filas(self) -> list[list[str]]:
        """Filas para la tabla de trazabilidad del PDF."""
        out = []
        for m in self.mediciones:
            out.append([
                m.fuente,
                m.objeto,
                f"{m.bytes_leidos / 1024:,.0f} KB".replace(",", "."),
                f"{m.filas_origen:,}".replace(",", "."),
                f"{m.filas_filtradas:,}".replace(",", "."),
                f"{m.ms_minio:,.0f}".replace(",", "."),
                f"{m.ms_parseo:,.0f}".replace(",", "."),
                f"{m.ms_filtro:,.0f}".replace(",", "."),
            ])
        return out


def _leer_medido(cron: Cronometro, etiqueta: str, objeto: str,
                 bucket: str = BUCKET_APP) -> pd.DataFrame:
    """Descarga y parsea un Parquet midiendo cada etapa por separado."""
    m = Medicion(fuente=etiqueta, objeto=f"{bucket}/{objeto}")
    try:
        t0 = time.perf_counter()
        resp = get_cliente().get_object(bucket, objeto)
        crudo = resp.read()
        try:
            resp.close()
            resp.release_conn()
        except Exception:
            pass
        m.ms_minio = (time.perf_counter() - t0) * 1000
        m.bytes_leidos = len(crudo)

        t1 = time.perf_counter()
        df = pd.read_parquet(io.BytesIO(crudo))
        m.ms_parseo = (time.perf_counter() - t1) * 1000
        m.filas_origen = int(len(df))
        m.filas_filtradas = int(len(df))
        cron.añadir(m)
        return df
    except Exception as e:
        m.error = f"{type(e).__name__}: {e}"
        cron.añadir(m)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Registro de fuentes por departamento
# ---------------------------------------------------------------------------
# columnas: (campo, etiqueta, peso_ancho, alineacion)
@dataclass
class Fuente:
    titulo: str
    objeto: str
    columnas: list[tuple[str, str, float, str]]
    campo_fecha: str = ""
    campo_sede: str = ""
    campo_genero: str = ""
    campo_edad: str = ""
    orden: str = ""
    enriquecer_paciente: bool = False


FUENTES: dict[str, Fuente] = {
    "citas": Fuente(
        titulo="Agenda de citas",
        objeto="operativo/citas.parquet",
        columnas=[
            ("fecha", "Fecha", 1.0, "L"),
            ("hora", "Hora", 0.6, "C"),
            ("paciente_nombre", "Paciente", 2.3, "L"),
            ("medico", "Médico", 1.8, "L"),
            ("motivo", "Motivo", 2.2, "L"),
            ("sede", "Sede", 1.4, "L"),
            ("estado", "Estado", 1.0, "C"),
        ],
        campo_fecha="fecha", campo_sede="sede", orden="fecha",
    ),
    "pacientes": Fuente(
        titulo="Padrón de pacientes",
        objeto="operativo/pacientes.parquet",
        columnas=[
            ("codigo", "H. clínica", 1.3, "L"),
            ("documento", "Documento", 1.3, "L"),
            ("nombre_completo", "Paciente", 2.6, "L"),
            ("edad", "Edad", 0.6, "C"),
            ("genero", "Género", 1.0, "L"),
            ("sede", "Sede", 1.6, "L"),
            ("estado", "Estado", 0.9, "C"),
        ],
        # Sin campo_fecha a proposito: el padron es maestro, no una serie del
        # periodo. Filtrarlo por `creado_en` dejaba el listado en cero cuando
        # el alta del expediente no caia en el año consultado.
        campo_sede="sede", campo_genero="genero", campo_edad="edad",
        orden="codigo",
    ),
    "admisiones": Fuente(
        titulo="Admisiones",
        objeto="operativo/admisiones.parquet",
        columnas=[
            ("fecha_ingreso", "Ingreso", 1.1, "L"),
            ("paciente_nombre", "Paciente", 2.3, "L"),
            ("tipo", "Tipo", 1.1, "L"),
            ("servicio", "Servicio", 1.8, "L"),
            ("medico_nombre", "Médico", 1.7, "L"),
            ("habitacion", "Hab.", 0.8, "C"),
            ("estado", "Estado", 0.9, "C"),
        ],
        campo_fecha="fecha_ingreso", campo_sede="sede", orden="fecha_ingreso",
    ),
    "urgencias": Fuente(
        titulo="Urgencias",
        objeto="negocio/hechos_emergencia.parquet",
        columnas=[
            ("hora_llegada", "Llegada", 1.3, "L"),
            ("paciente_nombre", "Paciente", 2.4, "L"),
            ("triage", "Triage", 0.9, "C"),
            ("motivo", "Motivo", 2.2, "L"),
            ("via_llegada", "Vía", 1.2, "L"),
            ("desenlace", "Desenlace", 1.3, "L"),
            ("estado", "Estado", 1.0, "C"),
        ],
        campo_fecha="hora_llegada", orden="hora_llegada",
        enriquecer_paciente=True,
    ),
    "laboratorio": Fuente(
        titulo="Órdenes de laboratorio",
        objeto="negocio/oper_ordenes_lab.parquet",
        columnas=[
            ("fecha", "Fecha", 1.2, "L"),
            ("id_orden", "Orden", 1.6, "L"),
            ("paciente_nombre", "Paciente", 2.8, "L"),
            ("id_prueba", "Prueba", 1.6, "L"),
            ("encounter_id", "Encuentro", 1.2, "R"),
            ("estado", "Estado", 1.2, "C"),
        ],
        campo_fecha="fecha", orden="fecha", enriquecer_paciente=True,
    ),
    "caja": Fuente(
        titulo="Facturación",
        objeto="negocio/hechos_facturacion.parquet",
        columnas=[
            ("fecha", "Fecha", 1.2, "L"),
            ("id_factura", "Factura", 1.7, "L"),
            ("paciente_nombre", "Paciente", 2.6, "L"),
            ("subtotal", "Subtotal", 1.1, "R"),
            ("iva", "IVA", 0.9, "R"),
            ("total", "Total", 1.1, "R"),
            ("estado", "Estado", 1.1, "C"),
        ],
        campo_fecha="fecha", orden="fecha", enriquecer_paciente=True,
    ),
    "farmacia": Fuente(
        titulo="Recetas y dispensación",
        objeto="negocio/oper_recetas.parquet",
        columnas=[
            ("fecha", "Fecha", 1.2, "L"),
            ("id_receta", "Receta", 1.7, "L"),
            ("paciente_nombre", "Paciente", 2.7, "L"),
            ("indicaciones", "Indicaciones", 2.6, "L"),
            ("estado", "Estado", 1.2, "C"),
        ],
        campo_fecha="fecha", orden="fecha", enriquecer_paciente=True,
    ),
    "comorbilidades": Fuente(
        titulo="Comorbilidades registradas",
        objeto="negocio/oper_comorbilidades_paciente.parquet",
        columnas=[
            ("fecha_deteccion", "Detección", 1.3, "L"),
            ("paciente_nombre", "Paciente", 2.8, "L"),
            ("tipo", "Comorbilidad", 2.2, "L"),
            ("notas", "Notas", 2.4, "L"),
            ("estado", "Estado", 1.1, "C"),
        ],
        campo_fecha="fecha_deteccion", orden="fecha_deteccion",
        enriquecer_paciente=True,
    ),
    "rrhh": Fuente(
        titulo="Costeo de personal",
        objeto="negocio/oper_personal_costo.parquet",
        columnas=[
            ("id_personal", "Personal", 2.4, "L"),
            ("id_cargo", "Cargo", 2.4, "L"),
            ("costo_hora", "Costo/hora", 1.4, "R"),
            ("fecha_vigencia", "Vigencia", 1.6, "L"),
            ("activo", "Activo", 1.0, "C"),
        ],
        # Igual que el padron: la tarifa vigente es maestro, no evento del periodo.
        orden="fecha_vigencia",
    ),
}


def _fmt_celda(valor, campo: str) -> str:
    if valor is None:
        return ""
    txt = str(valor)
    if txt.lower() in ("nan", "nat", "none"):
        return ""
    if campo in ("subtotal", "descuento", "iva", "total", "costo_hora", "costo_unitario"):
        try:
            return f"{float(valor):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
        except (TypeError, ValueError):
            return txt
    if campo in ("edad", "age", "encounter_id", "cantidad"):
        try:
            return str(int(round(float(valor))))
        except (TypeError, ValueError):
            return txt
    # Los identificadores son UUID: en papel solo estorban, basta el prefijo.
    if campo.startswith("id_") and len(txt) == 36 and txt.count("-") == 4:
        return txt[:8]
    # Fechas ISO con hora: dejar solo lo legible
    if len(txt) >= 19 and txt[4] == "-" and txt[10] in ("T", " "):
        return txt[:16].replace("T", " ")
    if len(txt) > 10 and txt[4] == "-" and txt[7] == "-":
        return txt[:10]
    return txt


def _aplicar_filtros(df: pd.DataFrame, f: Fuente, filtros: dict) -> pd.DataFrame:
    """Aplica solo los filtros que la fuente puede honrar."""
    if df.empty:
        return df
    year = filtros.get("year")
    if year and f.campo_fecha and f.campo_fecha in df.columns:
        df = df[df[f.campo_fecha].astype(str).str.startswith(str(int(year)))]
    loc = str(filtros.get("location") or "").strip()
    if loc and f.campo_sede and f.campo_sede in df.columns:
        df = df[df[f.campo_sede].astype(str).str.contains(loc, case=False, na=False)]
    gen = str(filtros.get("gender") or "").strip()
    if gen and f.campo_genero and f.campo_genero in df.columns:
        df = df[df[f.campo_genero].astype(str).str.lower() == gen.lower()]
    if f.campo_edad and f.campo_edad in df.columns:
        edad = pd.to_numeric(df[f.campo_edad], errors="coerce")
        if filtros.get("age_min") is not None:
            df = df[edad >= float(filtros["age_min"])]
            edad = edad.loc[df.index]
        if filtros.get("age_max") is not None:
            df = df[edad <= float(filtros["age_max"])]
    return df


def _nombre_completo(df: pd.DataFrame) -> pd.DataFrame:
    """El padrón guarda nombre y apellido por separado; el informe los junta."""
    if df.empty or "nombre_completo" in df.columns:
        return df
    if "nombre" not in df.columns and "apellido" not in df.columns:
        return df
    df = df.copy()
    nom = df.get("nombre", "").fillna("").astype(str).str.strip() if "nombre" in df.columns else ""
    ape = df.get("apellido", "").fillna("").astype(str).str.strip() if "apellido" in df.columns else ""
    df["nombre_completo"] = (nom + " " + ape).str.strip() if isinstance(nom, pd.Series) else ape
    return df


def _enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    """Cambia id_paciente por el nombre real (un informe con UUIDs no sirve)."""
    if df.empty or "id_paciente" not in df.columns:
        if "paciente_nombre" not in df.columns:
            df = df.copy()
            df["paciente_nombre"] = ""
        return df
    df = df.copy()
    try:
        from nucleo.utilidades.PacientesLookup import mapa_pacientes
        ids = {str(x) for x in df["id_paciente"].dropna().astype(str).tolist()}
        mapa = mapa_pacientes(ids)
        df["paciente_nombre"] = df["id_paciente"].astype(str).map(
            lambda p: (mapa.get(p) or {}).get("nombre_completo") or p[:8]
        )
    except Exception:
        df["paciente_nombre"] = df["id_paciente"].astype(str).str.slice(0, 8)
    return df


def detalle(clave: str, filtros: dict, cron: Cronometro,
            limite: int = LIMITE_FILAS) -> dict | None:
    """
    Filas reales de un departamento.

    Devuelve cabeceras/filas listas para el PDF más el conteo total, para poder
    declarar en el informe cuántas de cuántas se están mostrando.
    """
    f = FUENTES.get(clave)
    if not f:
        return None
    df = _leer_medido(cron, f.titulo, f.objeto)
    med = cron.mediciones[-1]
    if df.empty:
        return {
            "titulo": f.titulo, "objeto": f.objeto,
            "cabeceras": [c[1] for c in f.columnas], "filas": [],
            "total": 0, "mostradas": 0, "truncado": False,
            "error": med.error,
        }

    t0 = time.perf_counter()
    df = _aplicar_filtros(df, f, filtros)
    if f.enriquecer_paciente:
        df = _enriquecer(df)
    df = _nombre_completo(df)
    total = int(len(df))
    if f.orden and f.orden in df.columns:
        df = df.sort_values(f.orden, ascending=False)
    pagina = df.head(limite)
    med.ms_filtro = (time.perf_counter() - t0) * 1000
    med.filas_filtradas = total

    filas = []
    for reg in pagina.to_dict(orient="records"):
        filas.append([_fmt_celda(reg.get(c[0]), c[0]) for c in f.columnas])

    return {
        "titulo": f.titulo,
        "objeto": f.objeto,
        "cabeceras": [c[1] for c in f.columnas],
        "pesos": [c[2] for c in f.columnas],
        "alineaciones": [c[3] for c in f.columnas],
        "filas": filas,
        "total": total,
        "mostradas": len(filas),
        "truncado": total > len(filas),
        "error": "",
    }


# ---------------------------------------------------------------------------
# Detalle clínico (stage/, el dataset grande)
# ---------------------------------------------------------------------------
_COLS_CLINICO = [
    ("encounter_id", "Encuentro", 1.1, "R"),
    ("paciente_nombre", "Paciente", 2.4, "L"),
    ("age", "Edad", 0.6, "C"),
    ("gender", "Género", 1.0, "L"),
    ("bmi", "BMI", 0.7, "R"),
    ("hbA1c_level", "HbA1c", 0.8, "R"),
    ("blood_glucose_level", "Glucosa", 0.9, "R"),
    ("hypertension", "HTA", 0.6, "C"),
    ("heart_disease", "Cardio", 0.7, "C"),
    ("diabetes", "DM", 0.6, "C"),
    ("location", "Sede", 1.5, "L"),
    ("year", "Año", 0.7, "C"),
]


def detalle_clinico(filtros: dict, cron: Cronometro,
                    limite: int = LIMITE_CLINICO) -> dict:
    """
    Encuentros clínicos reales del stage, con los filtros del informe aplicados.

    El total se calcula sobre el dataset completo (vectorizado) para no mentir
    en el "mostrando X de Y", aunque solo se materialicen `limite` filas.
    """
    objeto = f"{MINIO_STAGE_PATH}diabcare_registros.parquet"
    df = pd.DataFrame()
    try:
        c = get_cliente()
        candidatos = sorted(
            (o.object_name for o in c.list_objects(MINIO_BUCKET, prefix=MINIO_STAGE_PATH, recursive=True)
             if o.object_name.endswith(".parquet")),
        )
        if candidatos:
            objeto = candidatos[-1]
    except Exception:
        pass

    df = _leer_medido(cron, "Encuentros clínicos", objeto, bucket=MINIO_BUCKET)
    med = cron.mediciones[-1]
    cab = [c[1] for c in _COLS_CLINICO]
    if df.empty:
        return {"titulo": "Encuentros clínicos", "objeto": objeto, "cabeceras": cab,
                "pesos": [c[2] for c in _COLS_CLINICO],
                "alineaciones": [c[3] for c in _COLS_CLINICO],
                "filas": [], "total": 0, "mostradas": 0, "truncado": False,
                "error": med.error}

    t0 = time.perf_counter()
    if filtros.get("year") is not None and "year" in df.columns:
        df = df[pd.to_numeric(df["year"], errors="coerce") == int(filtros["year"])]
    if filtros.get("diabetes") is not None and "diabetes" in df.columns:
        df = df[pd.to_numeric(df["diabetes"], errors="coerce") == int(filtros["diabetes"])]
    gen = str(filtros.get("gender") or "").strip()
    if gen and "gender" in df.columns:
        df = df[df["gender"].astype(str).str.lower() == gen.lower()]
    loc = str(filtros.get("location") or "").strip()
    if loc and "location" in df.columns:
        df = df[df["location"].astype(str).str.contains(loc, case=False, na=False)]
    if "age" in df.columns:
        edad = pd.to_numeric(df["age"], errors="coerce")
        if filtros.get("age_min") is not None:
            df = df[edad >= float(filtros["age_min"])]
            edad = edad.loc[df.index]
        if filtros.get("age_max") is not None:
            df = df[edad <= float(filtros["age_max"])]

    total = int(len(df))
    pagina = df.head(limite).copy()
    if "id_paciente" in pagina.columns:
        pagina = _enriquecer(pagina)
    elif "paciente_nombre" not in pagina.columns:
        pagina["paciente_nombre"] = ""
    med.ms_filtro = (time.perf_counter() - t0) * 1000
    med.filas_filtradas = total

    filas = []
    for reg in pagina.to_dict(orient="records"):
        fila = []
        for campo, _lab, _p, _al in _COLS_CLINICO:
            v = reg.get(campo)
            if campo in ("hypertension", "heart_disease", "diabetes"):
                try:
                    fila.append("Sí" if int(float(v)) == 1 else "No")
                except (TypeError, ValueError):
                    fila.append("")
            elif campo in ("bmi", "hbA1c_level"):
                try:
                    fila.append(f"{float(v):.1f}".replace(".", ","))
                except (TypeError, ValueError):
                    fila.append("")
            else:
                fila.append(_fmt_celda(v, campo))
        filas.append(fila)

    return {
        "titulo": "Encuentros clínicos",
        "objeto": objeto,
        "cabeceras": cab,
        "pesos": [c[2] for c in _COLS_CLINICO],
        "alineaciones": [c[3] for c in _COLS_CLINICO],
        "filas": filas,
        "total": total,
        "mostradas": len(filas),
        "truncado": total > len(filas),
        "error": "",
    }
